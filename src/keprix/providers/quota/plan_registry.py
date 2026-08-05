"""Default quota plans for provider tiers."""

from __future__ import annotations

DEFAULT_PROVIDER_PLANS: dict[str, dict[str, int | str]] = {
    "kiro": {"tier": "free_forever", "daily_tokens": 50_000},
    "qoder": {"tier": "free_forever", "daily_tokens": 50_000},
    "pollinations": {"tier": "free_forever", "daily_tokens": 100_000},
    "deepseek": {"tier": "api_keys", "daily_tokens": 1_000_000},
    "groq": {"tier": "api_keys", "daily_tokens": 500_000},
    "xai": {"tier": "api_keys", "daily_tokens": 500_000},
    "mistral": {"tier": "api_keys", "daily_tokens": 500_000},
    "openai": {"tier": "api_keys", "daily_tokens": 500_000},
    "ollama": {"tier": "fallback", "daily_tokens": 0},
    "lm_studio": {"tier": "fallback", "daily_tokens": 0},
}


def get_plan(provider: str) -> dict[str, int | str]:
    return DEFAULT_PROVIDER_PLANS.get(provider, {"tier": "unknown", "daily_tokens": 0})
