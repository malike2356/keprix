"""GUI-managed Syncthing config (no .env required)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from keprix_constants import get_keprix_home
from keprix.sync.syncthing.types import DEFAULT_CONFIG, SyncthingConfig, WriterRole
from keprix.vault.config import coerce_vault_root, get_vault_config


def _config_path() -> Path:
    path = get_keprix_home() / "config" / "syncthing.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _api_key_path() -> Path:
    path = get_keprix_home() / "data" / "syncthing" / "api-key"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def default_vault_path() -> str:
    vault = get_vault_config()
    if vault.root_path:
        return coerce_vault_root(vault.root_path)
    return str(get_keprix_home() / "vault")


def normalize_config(raw: dict[str, Any] | None = None) -> SyncthingConfig:
    base = {**DEFAULT_CONFIG.to_dict(), **(raw or {})}
    aliases = {
        "baseUrl": "base_url",
        "folderId": "folder_id",
        "folderLabel": "folder_label",
        "vaultPath": "vault_path",
        "syncthingPath": "syncthing_path",
        "writerRole": "writer_role",
        "deviceIds": "device_ids",
        "rescanIntervalS": "rescan_interval_s",
        "lastError": "last_error",
        "lastOkAt": "last_ok_at",
    }
    for src, dest in aliases.items():
        if src in base and dest not in (raw or {}):
            base[dest] = base[src]
    role = str(base.get("writer_role") or "home")
    if role not in {"home", "keprix", "both"}:
        role = "home"
    devices = base.get("device_ids") or []
    if isinstance(devices, str):
        devices = [part.strip() for part in devices.replace("\n", ",").split(",") if part.strip()]
    vault_path = str(base.get("vault_path") or "").strip() or default_vault_path()
    syncthing_path = str(base.get("syncthing_path") or "").strip() or vault_path
    return SyncthingConfig(
        enabled=bool(base.get("enabled")),
        base_url=str(base.get("base_url") or DEFAULT_CONFIG.base_url).rstrip("/"),
        folder_id=str(base.get("folder_id") or DEFAULT_CONFIG.folder_id).strip() or DEFAULT_CONFIG.folder_id,
        folder_label=str(base.get("folder_label") or DEFAULT_CONFIG.folder_label).strip() or DEFAULT_CONFIG.folder_label,
        vault_path=vault_path,
        syncthing_path=syncthing_path,
        writer_role=role,  # type: ignore[arg-type]
        device_ids=[str(item).strip() for item in devices if str(item).strip()],
        rescan_interval_s=max(10, int(base.get("rescan_interval_s") or 60)),
        last_error=base.get("last_error"),
        last_ok_at=base.get("last_ok_at"),
    )


def load_config() -> SyncthingConfig:
    path = _config_path()
    if path.is_file():
        try:
            return normalize_config(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return normalize_config({"vault_path": default_vault_path()})


def save_config(patch: dict[str, Any]) -> SyncthingConfig:
    current = load_config()
    next_cfg = normalize_config({**current.to_dict(), **patch})
    path = _config_path()
    path.write_text(json.dumps(next_cfg.to_dict(), indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return next_cfg


def load_api_key() -> str | None:
    path = _api_key_path()
    if path.is_file():
        key = path.read_text(encoding="utf-8").strip()
        if key:
            return key
    # Optional bootstrap only
    env = (os.getenv("SYNCTHING_API_KEY") or os.getenv("KEPRIX_SYNCTHING_API_KEY") or "").strip()
    return env or None


def save_api_key(api_key: str | None) -> None:
    path = _api_key_path()
    if not api_key or not str(api_key).strip():
        if path.exists():
            path.unlink()
        return
    path.write_text(f"{api_key.strip()}\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def has_api_key() -> bool:
    return bool(load_api_key())


def folder_type_for_role(role: WriterRole) -> str:
    from keprix.sync.syncthing.types import ONE_WRITER_RULES

    return str(ONE_WRITER_RULES[role]["local_folder_type"])
