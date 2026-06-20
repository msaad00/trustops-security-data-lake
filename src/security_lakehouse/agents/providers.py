"""Model provider configuration for optional agent runs."""

from __future__ import annotations

import os
from dataclasses import dataclass


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

    @property
    def enabled(self) -> bool:
        if self.provider in {"", "rules_only"}:
            return False
        if self.provider == "ollama":
            return bool(self.base_url)
        return bool(self.api_key_env and os.environ.get(self.api_key_env))


def provider_from_env() -> ModelProviderConfig:
    """Load optional model settings from environment."""
    provider = os.environ.get("TRUSTOPS_AGENT_PROVIDER", "rules_only").strip().lower()
    if provider in {"", "none", "off"}:
        provider = "rules_only"
    default_key_env = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }.get(provider, "")
    return ModelProviderConfig(
        provider=provider,
        model=os.environ.get("TRUSTOPS_AGENT_MODEL", ""),
        base_url=os.environ.get("TRUSTOPS_AGENT_BASE_URL", "http://127.0.0.1:11434" if provider == "ollama" else ""),
        api_key_env=os.environ.get("TRUSTOPS_AGENT_API_KEY_ENV", default_key_env),
    )
