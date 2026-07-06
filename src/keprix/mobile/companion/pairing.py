"""Companion device pairing for mobile native apps (Prompt 25)."""

from __future__ import annotations

import json
import secrets
import socket
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PAIRING_VERSION = 1
COMPANION_SCOPE = "mobile_companion"
PAIRING_TTL_SECONDS = 600


def _store_dir() -> Path:
    import os

    base = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if base:
        root = Path(base) / "companion"
    else:
        try:
            from keprix_cli.config import get_keprix_home

            root = Path(get_keprix_home()) / "companion"
        except Exception:
            root = Path.home() / ".keprix" / "companion"
    root.mkdir(parents=True, exist_ok=True)
    return root


class CompanionPairingStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _store_dir()
        self._pending_path = self._dir / "pending_pairings.json"
        self._devices_path = self._dir / "paired_devices.json"

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def create_pairing(self, workspace_id: str, *, created_by: str) -> dict[str, Any]:
        code = secrets.token_hex(3).upper()
        pairing_id = str(uuid.uuid4())
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=PAIRING_TTL_SECONDS)).isoformat()
        payload = {
            "pairing_id": pairing_id,
            "workspace_id": workspace_id,
            "code": code,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
            "confirmed": False,
        }
        pending = self._read_json(self._pending_path)
        pending[pairing_id] = payload
        self._write_json(self._pending_path, pending)
        return payload

    def confirm_pairing(
        self,
        pairing_id: str,
        *,
        code: str,
        device_name: str,
        platform: str,
    ) -> dict[str, Any] | None:
        pending = self._read_json(self._pending_path)
        row = pending.get(pairing_id)
        if not row or row.get("confirmed"):
            return None
        if str(row.get("code")) != code:
            return None
        expires_at = datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            return None

        from keprix.public_api.keys import ApiKeyStore
        from keprix.public_api.schemas import CreateApiKeyRequest

        created = ApiKeyStore().create(
            CreateApiKeyRequest(
                name=f"companion:{device_name}",
                workspace_id=str(row.get("workspace_id") or "default"),
                role="user",
                scopes={"companion": True},
                allowed_models=[],
                allowed_endpoints=["/api/notifications/inbox", "/api/conversation"],
            )
        )
        device = {
            "id": str(uuid.uuid4()),
            "pairing_id": pairing_id,
            "workspace_id": row.get("workspace_id"),
            "device_name": device_name,
            "platform": platform,
            "api_key_id": created.id,
            "paired_at": datetime.now(timezone.utc).isoformat(),
        }
        devices = self._read_json(self._devices_path)
        devices[device["id"]] = device
        self._write_json(self._devices_path, devices)
        row["confirmed"] = True
        pending[pairing_id] = row
        self._write_json(self._pending_path, pending)
        return {"device": device, "token": created.secret}

    def list_paired(self, workspace_id: str) -> list[dict[str, Any]]:
        devices = self._read_json(self._devices_path)
        return [
            row
            for row in devices.values()
            if str(row.get("workspace_id") or "default") == workspace_id
        ]

    def unpair(self, device_id: str) -> bool:
        devices = self._read_json(self._devices_path)
        row = devices.pop(device_id, None)
        if not row:
            return False
        self._write_json(self._devices_path, devices)
        from keprix.public_api.keys import get_api_key_store

        get_api_key_store().revoke(str(row.get("api_key_id")))
        return True


def lan_ip_candidates() -> list[str]:
    candidates: list[str] = []

    def _add(ip: str) -> None:
        if ip and ip not in candidates and not ip.startswith("127."):
            candidates.append(ip)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        _add(sock.getsockname()[0])
    except OSError:
        pass
    finally:
        sock.close()
    return candidates


def pairing_qr_payload(*, server_url: str, pairing_id: str, code: str) -> dict[str, Any]:
    return {
        "v": PAIRING_VERSION,
        "server_url": server_url.rstrip("/"),
        "pairing_id": pairing_id,
        "code": code,
    }


def pairing_qr_png_data_uri(payload: dict[str, Any]) -> str | None:
    try:
        import base64
        import io

        import qrcode

        img = qrcode.make(json.dumps(payload, separators=(",", ":")))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


_store: CompanionPairingStore | None = None


def get_companion_store() -> CompanionPairingStore:
    global _store
    if _store is None:
        _store = CompanionPairingStore()
    return _store


def reset_companion_store() -> None:
    global _store
    _store = None
