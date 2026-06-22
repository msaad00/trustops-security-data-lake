"""Small dependency-free clients for optional model-assisted agent runs."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from security_lakehouse.agents.model_contract import model_messages
from security_lakehouse.agents.providers import ModelProviderConfig


class ModelClientError(RuntimeError):
    """Raised when an optional model provider cannot return usable JSON."""


def call_model_json(context: dict[str, Any], provider: ModelProviderConfig) -> dict[str, Any]:
    """Call the configured provider and return parsed JSON.

    This is deliberately optional and dependency-free. TrustOps remains useful
    when this function is never called.
    """
    if provider.provider == "ollama":
        return _call_ollama(context, provider)
    if provider.provider in {"openai", "openai_compatible"}:
        return _call_openai_compatible(context, provider)
    if provider.provider == "anthropic":
        return _call_anthropic(context, provider)
    raise ModelClientError(f"unsupported model provider: {provider.provider}")


def _post_json(url: str, payload: dict[str, Any], *, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise ModelClientError(str(exc)) from exc


def _parse_json_content(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ModelClientError("model returned non-JSON content") from exc
    if not isinstance(payload, dict):
        raise ModelClientError("model returned JSON that is not an object")
    return payload


def _call_ollama(context: dict[str, Any], provider: ModelProviderConfig) -> dict[str, Any]:
    if not provider.model:
        raise ModelClientError("TRUSTOPS_AGENT_MODEL is required for ollama")
    url = provider.base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": provider.model,
        "messages": model_messages(context),
        "format": "json",
        "stream": False,
    }
    response = _post_json(url, payload, headers={"Content-Type": "application/json"}, timeout=provider.timeout_seconds)
    message = response.get("message") if isinstance(response.get("message"), dict) else {}
    return _parse_json_content(str(message.get("content") or ""))


def _call_openai_compatible(context: dict[str, Any], provider: ModelProviderConfig) -> dict[str, Any]:
    if not provider.model:
        raise ModelClientError("TRUSTOPS_AGENT_MODEL is required for OpenAI-compatible providers")
    api_key = os.environ.get(provider.api_key_env)
    if not api_key:
        raise ModelClientError(f"{provider.api_key_env} is not set")
    base_url = provider.base_url.rstrip("/") if provider.base_url else "https://api.openai.com/v1"
    payload = {
        "model": provider.model,
        "messages": model_messages(context),
        "response_format": {"type": "json_object"},
    }
    response = _post_json(
        base_url + "/chat/completions",
        payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        timeout=provider.timeout_seconds,
    )
    choices = response.get("choices") if isinstance(response.get("choices"), list) else []
    message = choices[0].get("message") if choices and isinstance(choices[0], dict) else {}
    return _parse_json_content(str(message.get("content") or ""))


def _call_anthropic(context: dict[str, Any], provider: ModelProviderConfig) -> dict[str, Any]:
    if not provider.model:
        raise ModelClientError("TRUSTOPS_AGENT_MODEL is required for anthropic")
    api_key = os.environ.get(provider.api_key_env)
    if not api_key:
        raise ModelClientError(f"{provider.api_key_env} is not set")
    messages = model_messages(context)
    payload = {
        "model": provider.model,
        "max_tokens": 1200,
        "system": messages[0]["content"],
        "messages": [{"role": "user", "content": messages[1]["content"]}],
    }
    response = _post_json(
        (provider.base_url.rstrip("/") if provider.base_url else "https://api.anthropic.com") + "/v1/messages",
        payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout=provider.timeout_seconds,
    )
    blocks = response.get("content") if isinstance(response.get("content"), list) else []
    first = blocks[0] if blocks and isinstance(blocks[0], dict) else {}
    return _parse_json_content(str(first.get("text") or ""))
