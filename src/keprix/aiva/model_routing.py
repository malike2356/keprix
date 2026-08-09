"""Config-driven, tool-capable model routing for Aiva agent turns."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_PROVIDER = "deepseek"
DEFAULT_MODEL = "deepseek-v4-flash"

_TIER_DEFAULTS: dict[str, tuple[str, str, int]] = {
    "starter": ("deepseek", "deepseek-v4-flash", 2000),
    "growth": ("anthropic", "claude-haiku-4-5", 2000),
    "business": ("anthropic", "claude-sonnet-4-6", 3000),
}

_TOOL_CAPABLE_MODELS = {
    "deepseek-v4-flash",
    "claude-haiku-4-5",
    "claude-sonnet-4-6",
    "gpt-4o-mini",
    "gemini-3.5-flash",
}

_NON_TOOL_MODEL_MARKERS = ("embed", "embedding", "stable-diffusion", "deepseek-r1")


@dataclass(frozen=True)
class AivaModelRoute:
    provider: str
    model: str
    tier: str
    source: str
    latency_target_ms: int

    @property
    def model_id(self) -> str:
        return f"{self.provider}:{self.model}"


def _clean(value: object) -> str:
    return str(value or "").strip()


def _normalized_tier(value: object) -> str:
    tier = _clean(value).lower()
    aliases = {"free": "starter", "pro": "growth", "premium": "business"}
    return aliases.get(tier, tier) if aliases.get(tier, tier) in _TIER_DEFAULTS else "starter"


def _split_model(value: str, fallback_provider: str) -> tuple[str, str]:
    if ":" in value:
        provider, model = value.split(":", 1)
        return _clean(provider).lower() or fallback_provider, _clean(model)
    return fallback_provider, value


def _workspace_routes(env: Mapping[str, str]) -> dict[str, object]:
    raw = _clean(env.get("AIVA_WORKSPACE_MODELS"))
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def model_supports_tools(provider: str, model: str) -> bool:
    """Reject known non-chat models; configured chat models default to capable."""
    del provider
    normalized = model.lower()
    if model in _TOOL_CAPABLE_MODELS:
        return True
    return not any(marker in normalized for marker in _NON_TOOL_MODEL_MARKERS)


def resolve_aiva_model(
    *,
    workspace_id: str,
    tier: str | None = None,
    workspace_model: str | None = None,
    workspace_provider: str | None = None,
    env: Mapping[str, str] | None = None,
    require_tools: bool = True,
) -> AivaModelRoute:
    """Resolve an Aiva model without changing the global engineering model."""
    values = os.environ if env is None else env
    resolved_tier = _normalized_tier(tier)
    tier_provider, tier_model, latency_target_ms = _TIER_DEFAULTS[resolved_tier]
    source = "tier"

    provider = _clean(workspace_provider).lower()
    model = _clean(workspace_model)
    if model:
        provider, model = _split_model(model, provider or tier_provider)
        source = "request_workspace_override"
    else:
        configured = _workspace_routes(values).get(workspace_id)
        if isinstance(configured, str) and _clean(configured):
            provider, model = _split_model(_clean(configured), tier_provider)
            source = "configured_workspace_override"
        elif isinstance(configured, dict) and _clean(configured.get("model")):
            provider = _clean(configured.get("provider")).lower() or tier_provider
            provider, model = _split_model(_clean(configured.get("model")), provider)
            source = "configured_workspace_override"
        elif resolved_tier == "starter":
            provider = _clean(values.get("AIVA_PROVIDER")).lower() or DEFAULT_PROVIDER
            configured_model = _clean(values.get("AIVA_MODEL")) or DEFAULT_MODEL
            provider, model = _split_model(configured_model, provider)
            source = "environment_default"
        else:
            provider, model = tier_provider, tier_model

    if not provider or not model:
        raise ValueError("Aiva model routing requires both provider and model")
    if require_tools and not model_supports_tools(provider, model):
        raise ValueError(f"Aiva model does not support required tools: {provider}:{model}")

    return AivaModelRoute(
        provider=provider,
        model=model,
        tier=resolved_tier,
        source=source,
        latency_target_ms=latency_target_ms,
    )
