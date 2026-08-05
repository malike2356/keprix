"""Syncthing service: vault-only folder wiring + one-writer enforcement."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.sync.syncthing.client import SyncthingClient, SyncthingError
from keprix.sync.syncthing.config import (
    folder_type_for_role,
    has_api_key,
    load_api_key,
    load_config,
    save_api_key,
    save_config,
)
from keprix.sync.syncthing.policy import one_writer_guidance, validate_separation
from keprix.sync.syncthing.types import WriterRole


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _agent_sync_clone_path() -> str | None:
    try:
        from keprix.sync.github_bridge import get_status

        status = get_status()
        return status.get("local_path") or status.get("localPath")
    except Exception:
        return None


def _apply_vault_read_only(read_only: bool) -> None:
    """Align vault.json read_only with one-writer role when Syncthing is enabled."""
    try:
        from keprix.vault.config import VaultConfig, get_vault_config, save_vault_config

        current = get_vault_config()
        root = current.root_path or str(Path(load_config().vault_path))
        save_vault_config(
            VaultConfig(
                provider=current.provider or "local_folder",
                root_path=root,
                watch=current.watch,
                read_only=read_only,
            )
        )
    except Exception:
        pass


def get_status() -> dict[str, Any]:
    cfg = load_config()
    guidance = one_writer_guidance(cfg.writer_role)
    warnings = validate_separation(vault_path=cfg.vault_path, agent_sync_clone=_agent_sync_clone_path())
    payload: dict[str, Any] = {
        "enabled": cfg.enabled,
        "configured": bool(cfg.base_url and has_api_key()),
        "has_api_key": has_api_key(),
        "base_url": cfg.base_url,
        "folder_id": cfg.folder_id,
        "folder_label": cfg.folder_label,
        "vault_path": cfg.vault_path,
        "syncthing_path": cfg.syncthing_path,
        "writer_role": cfg.writer_role,
        "folder_type": folder_type_for_role(cfg.writer_role),
        "device_ids": cfg.device_ids,
        "rescan_interval_s": cfg.rescan_interval_s,
        "one_writer": guidance,
        "warnings": warnings,
        "connected": False,
        "syncthing": None,
        "folder": None,
        "last_error": cfg.last_error,
        "last_ok_at": cfg.last_ok_at,
        # camelCase for UI
        "hasApiKey": has_api_key(),
        "baseUrl": cfg.base_url,
        "folderId": cfg.folder_id,
        "folderLabel": cfg.folder_label,
        "vaultPath": cfg.vault_path,
        "syncthingPath": cfg.syncthing_path,
        "writerRole": cfg.writer_role,
        "folderType": folder_type_for_role(cfg.writer_role),
        "deviceIds": cfg.device_ids,
        "rescanIntervalS": cfg.rescan_interval_s,
        "oneWriter": guidance,
        "lastError": cfg.last_error,
        "lastOkAt": cfg.last_ok_at,
    }
    if not cfg.enabled or not has_api_key():
        return payload
    try:
        client = SyncthingClient(cfg.base_url, load_api_key() or "")
        system = client.system_status()
        version = client.system_version()
        folder_stat = None
        try:
            folder_stat = client.folder_status(cfg.folder_id)
        except SyncthingError:
            folder_stat = None
        payload["connected"] = True
        payload["syncthing"] = {
            "my_id": system.get("myID"),
            "myId": system.get("myID"),
            "version": version.get("version"),
            "uptime": system.get("uptime"),
        }
        payload["folder"] = folder_stat
        save_config({"last_error": None, "last_ok_at": _now()})
        payload["last_error"] = None
        payload["lastError"] = None
        payload["last_ok_at"] = _now()
        payload["lastOkAt"] = payload["last_ok_at"]
    except SyncthingError as exc:
        payload["last_error"] = str(exc)
        payload["lastError"] = str(exc)
        save_config({"last_error": str(exc)})
    return payload


def update_settings(input_data: dict[str, Any]) -> dict[str, Any]:
    if "api_key" in input_data or "apiKey" in input_data:
        key = input_data.get("api_key", input_data.get("apiKey"))
        save_api_key(None if key is None else str(key) if key != "" else None)

    patch = {
        key: value
        for key, value in {
            "enabled": input_data.get("enabled"),
            "base_url": input_data.get("base_url", input_data.get("baseUrl")),
            "folder_id": input_data.get("folder_id", input_data.get("folderId")),
            "folder_label": input_data.get("folder_label", input_data.get("folderLabel")),
            "vault_path": input_data.get("vault_path", input_data.get("vaultPath")),
            "syncthing_path": input_data.get("syncthing_path", input_data.get("syncthingPath")),
            "writer_role": input_data.get("writer_role", input_data.get("writerRole")),
            "device_ids": input_data.get("device_ids", input_data.get("deviceIds")),
            "rescan_interval_s": input_data.get("rescan_interval_s", input_data.get("rescanIntervalS")),
        }.items()
        if value is not None
    }
    cfg = save_config(patch)
    warnings = validate_separation(vault_path=cfg.vault_path, agent_sync_clone=_agent_sync_clone_path())
    if any("overlaps" in w for w in warnings):
        # Hard-stop enable if path overlaps agent-sync
        if cfg.enabled:
            cfg = save_config({"enabled": False, "last_error": "; ".join(warnings)})
        return {**get_status(), "ok": False, "error": "; ".join(warnings)}

    guidance = one_writer_guidance(cfg.writer_role)
    if cfg.enabled:
        _apply_vault_read_only(bool(guidance.get("keprix_vault_read_only")))
        try:
            ensure_vault_folder()
        except SyncthingError as exc:
            save_config({"last_error": str(exc)})
    return get_status()


def ensure_vault_folder() -> dict[str, Any]:
    """Create/update the Syncthing folder for the Obsidian vault with one-writer type."""
    cfg = load_config()
    if not has_api_key():
        raise SyncthingError("Syncthing API key missing. Paste it in Settings -> Syncthing.")
    warnings = validate_separation(vault_path=cfg.vault_path, agent_sync_clone=_agent_sync_clone_path())
    if any("overlaps" in w for w in warnings):
        raise SyncthingError("; ".join(warnings))

    Path(cfg.vault_path).mkdir(parents=True, exist_ok=True)
    client = SyncthingClient(cfg.base_url, load_api_key() or "")
    config = client.get_config()
    folders = list(config.get("folders") or [])
    folder_type = folder_type_for_role(cfg.writer_role)
    devices = [{"deviceID": device_id} for device_id in cfg.device_ids]
    # Always include this device implicitly via Syncthing; listed peers are additional.
    existing_idx = next((i for i, f in enumerate(folders) if f.get("id") == cfg.folder_id), None)
    st_path = cfg.syncthing_path or cfg.vault_path
    folder_payload = {
        "id": cfg.folder_id,
        "label": cfg.folder_label,
        "path": st_path,
        "type": folder_type,
        "rescanIntervalS": cfg.rescan_interval_s,
        "fsWatcherEnabled": True,
        "devices": devices,
        "paused": False,
    }
    if existing_idx is None:
        folders.append(folder_payload)
    else:
        current = dict(folders[existing_idx])
        current.update(folder_payload)
        # Preserve existing devices if GUI did not list peers yet
        if not devices and current.get("devices"):
            current["devices"] = folders[existing_idx].get("devices") or []
        folders[existing_idx] = current
    config["folders"] = folders

    # Ensure peer devices exist in config
    device_list = list(config.get("devices") or [])
    known = {d.get("deviceID") for d in device_list}
    for device_id in cfg.device_ids:
        if device_id and device_id not in known:
            device_list.append({"deviceID": device_id, "name": f"keprix-peer-{device_id[:7]}"})
            known.add(device_id)
    config["devices"] = device_list

    client.put_config(config)
    guidance = one_writer_guidance(cfg.writer_role)
    _apply_vault_read_only(bool(guidance.get("keprix_vault_read_only")))
    save_config({"last_error": None, "last_ok_at": _now()})
    return {
        "ok": True,
        "folder_id": cfg.folder_id,
        "folder_type": folder_type,
        "vault_path": cfg.vault_path,
        "writer_role": cfg.writer_role,
        "one_writer": guidance,
        "warnings": warnings,
    }


def pause_folder(paused: bool = True) -> dict[str, Any]:
    cfg = load_config()
    client = SyncthingClient(cfg.base_url, load_api_key() or "")
    config = client.get_config()
    folders = list(config.get("folders") or [])
    found = False
    for folder in folders:
        if folder.get("id") == cfg.folder_id:
            folder["paused"] = paused
            found = True
    if not found:
        raise SyncthingError(f"Folder {cfg.folder_id} not found in Syncthing config")
    config["folders"] = folders
    client.put_config(config)
    return {"ok": True, "paused": paused, "folder_id": cfg.folder_id}
