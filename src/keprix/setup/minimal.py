"""Minimal one-screen provider setup for TUI unblock."""

from __future__ import annotations

from typing import Any

from keprix.api.chat_inference import PROVIDER_DEFAULT_MODELS

MINIMAL_PROVIDERS: dict[str, dict[str, str | tuple[str, ...] | None]] = {
    "openrouter": {
        "label": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
    },
    "openai": {
        "label": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "base_url": "",
    },
    "anthropic": {
        "label": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": "",
    },
    "ollama": {
        "label": "Ollama (local)",
        "env_key": None,
        "base_url": "http://127.0.0.1:11434/v1",
        "url_env": "OPENAI_BASE_URL",
    },
    "custom": {
        "label": "Custom OpenAI-compatible URL",
        "env_key": "OPENAI_API_KEY",
        "base_url": "",
        "url_env": "OPENAI_BASE_URL",
    },
}


def minimal_provider_catalog() -> list[dict[str, str]]:
    return [
        {"id": provider_id, "label": str(meta.get("label") or provider_id)}
        for provider_id, meta in MINIMAL_PROVIDERS.items()
    ]


def apply_minimal_setup(
    *,
    provider: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> dict[str, Any]:
    """Persist provider credentials and default model for first-run unblock."""
    provider_id = (provider or "").strip().lower()
    meta = MINIMAL_PROVIDERS.get(provider_id)
    if meta is None:
        raise ValueError(f"Unsupported provider: {provider}")

    from keprix_cli.auth import _save_model_choice, _update_config_for_provider, deactivate_provider
    from keprix_cli.config import save_env_value

    resolved_base = (base_url or str(meta.get("base_url") or "")).strip()
    env_key = meta.get("env_key")
    url_env = meta.get("url_env")

    if provider_id == "custom" and not resolved_base:
        raise ValueError("base_url is required for custom providers")

    if env_key and not api_key.strip():
        from keprix_cli.config import get_env_value

        if not get_env_value(str(env_key)):
            raise ValueError(f"api_key is required for {provider_id}")

    if env_key and api_key.strip():
        save_env_value(str(env_key), api_key.strip())

    if url_env and resolved_base:
        save_env_value(str(url_env), resolved_base.rstrip("/"))

    default_model = (model or "").strip() or PROVIDER_DEFAULT_MODELS.get(provider_id, "")

    inference_base = resolved_base
    if provider_id == "openrouter":
        inference_base = str(meta.get("base_url") or "https://openrouter.ai/api/v1")

    _update_config_for_provider(provider_id, inference_base, default_model=default_model or None)
    if default_model:
        _save_model_choice(default_model)
    deactivate_provider()

    from keprix.setup.status import setup_status_snapshot

    return {"ok": True, "status": setup_status_snapshot()}
