"""Model provider configuration for optional agent runs."""

from __future__ import annotations

import os
from dataclasses import dataclass

SUPPORTED_PROVIDERS = {"rules_only", "ollama", "openai", "openai_compatible", "anthropic"}


def _env_bool(name: str, *, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_provider(value: str) -> str:
    provider = value.strip().lower()
    if provider in {"", "none", "off"}:
        return "rules_only"
    if provider not in SUPPORTED_PROVIDERS:
        return "rules_only"
    return provider


@dataclass(frozen=True)
class ModelProviderConfig:
    """LLM provider settings.

    ``rules_only`` means no model is configured. Agent graphs must still run in
    this mode using deterministic TrustOps facts.
    """

    provider: str = "rules_only"
    model: str = ""
    base_url: str = ""
    api_key_env: str = ""
    use_model: bool = False
    timeout_seconds: float = 20.0

    @property
    def enabled(self) -> bool:
        if self.provider in {"", "rules_only"}:
            return False
        if self.provider == "ollama":
            return bool(self.base_url)
        return bool(self.api_key_env and os.environ.get(self.api_key_env))

    @property
    def should_call_model(self) -> bool:
        """Whether the harness should make a provider request."""
        return self.enabled and self.use_model

    def public_dict(self) -> dict[str, object]:
        """Return non-secret provider metadata suitable for audit output."""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "configured": self.enabled,
            "use_model": self.use_model,
            "timeout_seconds": self.timeout_seconds,
        }


def provider_from_env() -> ModelProviderConfig:
    """Load optional model settings from environment."""
    provider = normalize_provider(os.environ.get("TRUSTOPS_AGENT_PROVIDER", "rules_only"))
    default_key_env = {
        "openai": "OPENAI_API_KEY",
        "openai_compatible": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }.get(provider, "")
    timeout = os.environ.get("TRUSTOPS_AGENT_TIMEOUT_SECONDS", "20")
    try:
        timeout_seconds = max(1.0, min(float(timeout), 120.0))
    except ValueError:
        timeout_seconds = 20.0
    return ModelProviderConfig(
        provider=provider,
        model=os.environ.get("TRUSTOPS_AGENT_MODEL", ""),
        base_url=os.environ.get(
            "TRUSTOPS_AGENT_BASE_URL",
            "http://127.0.0.1:11434" if provider == "ollama" else "",
        ),
        api_key_env=os.environ.get("TRUSTOPS_AGENT_API_KEY_ENV", default_key_env),
        use_model=_env_bool("TRUSTOPS_AGENT_USE_MODEL"),
        timeout_seconds=timeout_seconds,
    )
