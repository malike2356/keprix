"""CRUD for user-defined OpenAI-compatible LLM providers (config.yaml custom_providers)."""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlparse

from keprix.api.chat_inference import invalidate_provider_cache

CUSTOM_PREFIX = "custom/"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", name.strip().lower()).strip("-")
    return slug[:64] or "custom-provider"


def _entry_id(entry: dict[str, Any]) -> str:
    explicit = str(entry.get("id") or "").strip()
    if explicit:
        return explicit
    return _slugify(str(entry.get("name") or "custom-provider"))


def _load_raw_list() -> list[dict[str, Any]]:
    try:
        from keprix_cli.config import load_config
    except Exception:
        return []

    cfg = load_config()
    providers = cfg.get("custom_providers") or []
    if not isinstance(providers, list):
        return []
    return [entry for entry in providers if isinstance(entry, dict)]


def _save_raw_list(providers: list[dict[str, Any]]) -> None:
    from keprix_cli.config import load_config, save_config

    cfg = load_config()
    cfg["custom_providers"] = providers
    save_config(cfg)
    invalidate_provider_cache()


def _public_key(provider_id: str) -> str:
    return f"{CUSTOM_PREFIX}{provider_id}"


def _normalize_base_url(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Base URL must be a valid http(s) endpoint")
    return cleaned


def _is_local_base_url(base_url: str) -> bool:
    host = urlparse(base_url).hostname or ""
    return host in {"localhost", "127.0.0.1", "::1"}


def serialize_custom_provider(entry: dict[str, Any]) -> dict[str, Any]:
    provider_id = _entry_id(entry)
    base_url = str(entry.get("base_url") or entry.get("api") or "").strip().rstrip("/")
    model = str(entry.get("model") or entry.get("default_model") or "").strip()
    api_key = str(entry.get("api_key") or "").strip()
    key_env = str(entry.get("key_env") or entry.get("api_key_env") or "").strip()
    api_key_set = bool(api_key or (key_env and os.getenv(key_env, "").strip()))
    connected = bool(base_url and (api_key_set or _is_local_base_url(base_url)))
    default_provider = os.getenv("KEPRIX_DEFAULT_PROVIDER", "").strip().lower()
    public_key = _public_key(provider_id).lower()
    return {
        "id": provider_id,
        "name": str(entry.get("name") or provider_id),
        "base_url": base_url,
        "default_model": model or None,
        "api_key_set": api_key_set,
        "connected": connected,
        "is_default": default_provider in {public_key, provider_id.lower(), f"custom-{provider_id.lower()}"},
        "kind": "custom",
    }


def list_custom_providers() -> list[dict[str, Any]]:
    return [serialize_custom_provider(entry) for entry in _load_raw_list()]


def get_custom_provider_raw(provider_id: str) -> dict[str, Any] | None:
    for entry in _load_raw_list():
        if _entry_id(entry) == provider_id:
            return entry
    return None


def get_custom_provider(provider_id: str) -> dict[str, Any] | None:
    entry = get_custom_provider_raw(provider_id)
    if entry is None:
        return None
    return serialize_custom_provider(entry)


def _unique_id(name: str, existing_ids: set[str]) -> str:
    base = _slugify(name)
    candidate = base
    suffix = 2
    while candidate in existing_ids:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def create_custom_provider(
    *,
    name: str,
    base_url: str,
    api_key: str | None = None,
    default_model: str | None = None,
) -> dict[str, Any]:
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Provider name is required")

    normalized_url = _normalize_base_url(base_url)
    providers = _load_raw_list()
    existing_ids = {_entry_id(entry) for entry in providers}
    provider_id = _unique_id(cleaned_name, existing_ids)

    entry: dict[str, Any] = {
        "id": provider_id,
        "name": cleaned_name,
        "base_url": normalized_url,
    }
    if api_key and api_key.strip():
        entry["api_key"] = api_key.strip()
    if default_model and default_model.strip():
        entry["model"] = default_model.strip()

    providers.append(entry)
    _save_raw_list(providers)
    return serialize_custom_provider(entry)


def update_custom_provider(
    provider_id: str,
    *,
    name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    default_model: str | None = None,
) -> dict[str, Any]:
    providers = _load_raw_list()
    updated: dict[str, Any] | None = None

    for index, entry in enumerate(providers):
        if _entry_id(entry) != provider_id:
            continue
        if name is not None and name.strip():
            entry["name"] = name.strip()
        if base_url is not None:
            entry["base_url"] = _normalize_base_url(base_url)
        if api_key is not None:
            cleaned = api_key.strip()
            if cleaned:
                entry["api_key"] = cleaned
            else:
                entry.pop("api_key", None)
        if default_model is not None:
            cleaned_model = default_model.strip()
            if cleaned_model:
                entry["model"] = cleaned_model
            else:
                entry.pop("model", None)
        providers[index] = entry
        updated = entry
        break

    if updated is None:
        raise KeyError(provider_id)

    _save_raw_list(providers)
    return serialize_custom_provider(updated)


def delete_custom_provider(provider_id: str) -> dict[str, Any]:
    providers = _load_raw_list()
    removed: dict[str, Any] | None = None
    kept: list[dict[str, Any]] = []

    for entry in providers:
        if _entry_id(entry) == provider_id:
            removed = entry
            continue
        kept.append(entry)

    if removed is None:
        raise KeyError(provider_id)

    public_key = _public_key(provider_id)
    if os.getenv("KEPRIX_DEFAULT_PROVIDER", "").strip().lower() in {
        public_key.lower(),
        provider_id.lower(),
    }:
        from keprix.api.provider_settings import remove_env_value

        remove_env_value("KEPRIX_DEFAULT_PROVIDER")

    _save_raw_list(kept)
    return serialize_custom_provider(removed)


def test_custom_provider(provider_id: str) -> dict[str, Any]:
    entry = get_custom_provider_raw(provider_id)
    if entry is None:
        return {"ok": False, "message": "Provider not found"}

    base_url = str(entry.get("base_url") or "").strip().rstrip("/")
    if not base_url:
        return {"ok": False, "message": "Base URL is not configured"}

    api_key = str(entry.get("api_key") or os.getenv(str(entry.get("key_env") or ""), "")).strip()
    if not api_key and not _is_local_base_url(base_url):
        return {"ok": False, "message": "API key is not configured"}

    models_url = f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"
    headers = {"Authorization": f"Bearer {api_key or 'no-key'}"}

    try:
        import httpx

        response = httpx.get(models_url, headers=headers, timeout=8.0)
        if response.status_code < 400:
            label = str(entry.get("name") or provider_id)
            model = str(entry.get("model") or "default")
            return {"ok": True, "message": f"{label} connected ({model})"}
        return {"ok": False, "message": f"Endpoint returned {response.status_code}"}
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:200]}
