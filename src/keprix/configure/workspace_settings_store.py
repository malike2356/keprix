"""Durable workspace preferences under KEPRIX_HOME."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from keprix.proxy.paths import keprix_home

_LOCK = threading.RLock()

DEFAULT_WORKSPACE_SETTINGS: dict[str, Any] = {
    "instance_name": "Keprix",
    "instance_url": "http://localhost:3333",
    "timezone": "UTC",
    "language": "en",
    "quiet_hours_enabled": False,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
    "max_tool_iterations": 20,
    "context_compression_threshold": 60000,
    "rtk_compression_enabled": False,
    "caveman_compression_enabled": False,
    "guardrails_pii_enabled": True,
    "guardrails_injection_enabled": True,
    "semantic_cache_enabled": False,
    "combo_routing_enabled": False,
    "mutation_engine_enabled": True,
    "mutation_sandbox_timeout": 30,
    "auto_approve_owner_mutations": False,
    "postgres_url": "",
    "redis_url": "",
    "vector_store_engine": "pgvector",
    "max_memory_documents": 1000,
    "governance_config": {
        "license_key": "",
        "audit_policy_url": "",
        "provider_endpoint": "",
    },
}

CONVERSATIONAL_KEYS = (
    "instance_name",
    "instance_url",
    "timezone",
    "language",
    "quiet_hours_enabled",
    "quiet_hours_start",
    "quiet_hours_end",
)


def settings_path() -> Path:
    return keprix_home() / "workspace_settings.json"


def load_workspace_settings() -> dict[str, Any]:
    with _LOCK:
        path = settings_path()
        data = deepcopy(DEFAULT_WORKSPACE_SETTINGS)
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    data.update(raw)
            except (OSError, json.JSONDecodeError):
                pass
        return data


def save_workspace_settings(updates: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        current = load_workspace_settings()
        for key, value in updates.items():
            if value is None:
                continue
            if key == "governance_config" and isinstance(value, dict):
                merged = dict(current.get("governance_config") or {})
                merged.update(value)
                current["governance_config"] = merged
            else:
                current[key] = value
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)
        try:
            path.chmod(0o600)
        except OSError:
            pass

    # Keep CLI timezone in sync when present
    tz = current.get("timezone")
    if isinstance(tz, str) and tz.strip():
        try:
            from keprix_cli.config import load_config, save_config

            cfg = load_config()
            if isinstance(cfg, dict):
                cfg["timezone"] = tz.strip()
                save_config(cfg)
        except Exception:
            pass
    return current


def public_workspace_settings() -> dict[str, Any]:
    data = load_workspace_settings()
    return {k: data.get(k) for k in CONVERSATIONAL_KEYS if k in data}
