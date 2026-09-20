"""First-run setup wizard state."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir


def _provider_registry() -> dict[str, Any]:
    try:
        from keprix_cli.auth import PROVIDER_REGISTRY
    except ImportError:
        from keprix.keprix_cli.auth import PROVIDER_REGISTRY
    return PROVIDER_REGISTRY


def wizard_llm_providers() -> list[dict[str, str]]:
    """API-key providers from the CLI registry. No named default."""
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for key, cfg in _provider_registry().items():
        if str(getattr(cfg, "auth_type", "") or "") != "api_key":
            continue
        provider_id = str(getattr(cfg, "id", "") or key).strip()
        if not provider_id or provider_id in seen:
            continue
        seen.add(provider_id)
        rows.append({
            "id": provider_id,
            "name": str(getattr(cfg, "name", "") or provider_id).strip(),
        })
    rows.sort(key=lambda row: (row["name"].lower(), row["id"]))
    return rows


def apply_wizard_provider_key(provider_id: str, api_key: str) -> dict[str, Any]:
    """Store a first-run key on whichever registry provider the owner picked."""
    registry = _provider_registry()
    cfg = registry.get(provider_id.strip())
    if cfg is None or str(getattr(cfg, "auth_type", "") or "") != "api_key":
        raise ValueError("Unknown provider")
    canonical = str(getattr(cfg, "id", "") or provider_id).strip()
    env_vars = tuple(getattr(cfg, "api_key_env_vars", ()) or ())
    if env_vars:
        _persist_provider_env(str(env_vars[0]), api_key.strip())
    _set_active_provider(canonical, str(getattr(cfg, "inference_base_url", "") or ""))
    return {"ok": True, "provider": canonical}


def _persist_provider_env(key: str, value: str) -> None:
    try:
        from keprix_cli.config import save_env_value
    except ImportError:
        from keprix.keprix_cli.config import save_env_value
    save_env_value(key, value)


def _set_active_provider(provider_id: str, inference_base_url: str) -> None:
    try:
        from keprix_cli.auth import _update_config_for_provider, deactivate_provider
    except ImportError:
        from keprix.keprix_cli.auth import _update_config_for_provider, deactivate_provider
    _update_config_for_provider(provider_id, inference_base_url)
    deactivate_provider()


def _marker_path() -> Path:
    return Path(data_dir()) / ".setup_complete"


def is_setup_complete() -> bool:
    env = os.environ.get("KEPRIX_SETUP_COMPLETE", "").strip().lower()
    if env in {"1", "true", "yes"}:
        return True
    return _marker_path().exists()


def is_public_setup_disabled() -> bool:
    """True on a deployment that's reachable by the public but is not an
    offering of hosted, multi-tenant access - e.g. the maintainer's own
    keprixai.com/app.keprixai.com marketing/demo instance. Keprix Community
    is self-hosted software: this instance already has its one owner, and
    the setup wizard (which creates THE owner account for whichever
    instance serves it) must never be presented to - or usable by - an
    anonymous visitor there. Every other self-hosted install leaves this
    unset and keeps the normal first-run wizard behavior."""
    env = os.environ.get("KEPRIX_PUBLIC_SETUP_DISABLED", "").strip().lower()
    return env in {"1", "true", "yes"}


def mark_setup_complete(*, owner_email: str | None = None) -> dict[str, Any]:
    base = Path(data_dir())
    base.mkdir(parents=True, exist_ok=True)
    payload = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "owner_email": owner_email,
    }
    _marker_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def wizard_status() -> dict[str, Any]:
    return {
        "complete": is_setup_complete(),
        "public_setup_disabled": is_public_setup_disabled(),
        "providers": wizard_llm_providers(),
    }


def credential_management_options() -> list[dict[str, Any]]:
    return [
        {"id": "external_vault", "label": "External vault", "recommended": True, "legacy": False},
        {"id": "cordon", "label": "Cordon proxy", "recommended": False, "legacy": False},
        {"id": "keprix_vault", "label": "Keprix encrypted vault", "recommended": False, "legacy": True},
        {"id": "env", "label": "Plain environment variables", "recommended": False, "legacy": True},
    ]
