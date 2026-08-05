"""Conversational companion device pairing."""

from __future__ import annotations

from typing import Any

from keprix.mobile.companion.pairing import (
    get_companion_store,
    lan_ip_candidates,
    pairing_qr_payload,
    pairing_qr_png_data_uri,
)


def list_companion_payload(workspace_id: str = "default") -> dict[str, Any]:
    devices = get_companion_store().list_paired(workspace_id)
    return {
        "devices": [
            {k: v for k, v in d.items() if k not in {"token", "api_key", "secret"}}
            for d in devices
        ],
        "workspace_id": workspace_id,
    }


def requirements_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "id": "companion",
        "name": "Companion device pairing",
        "description": "Pair a phone/desktop companion via short code + QR.",
        "flow": [
            "Call create to get pairing_id, code, qr_payload, and expires_at.",
            "Show the code (and QR if the client can render it) to the user.",
            "The device app confirms via /api/companion/pair/confirm.",
            "Use list to see paired devices; remove to unpair.",
        ],
        "hint": "Never speak API tokens. Prefer showing the pairing code in text UI.",
    }


def create_pairing_payload(
    *,
    workspace_id: str = "default",
    server_url: str | None = None,
    created_by: str = "admin",
) -> dict[str, Any]:
    pairing = get_companion_store().create_pairing(workspace_id, created_by=created_by)
    host = lan_ip_candidates()[0] if lan_ip_candidates() else "127.0.0.1"
    resolved = (server_url or f"http://{host}:8000").rstrip("/")
    payload = pairing_qr_payload(
        server_url=resolved,
        pairing_id=str(pairing["pairing_id"]),
        code=str(pairing["code"]),
    )
    return {
        "ok": True,
        "pairing_id": pairing["pairing_id"],
        "code": pairing["code"],
        "expires_at": pairing["expires_at"],
        "server_url": resolved,
        "qr_payload": payload,
        "qr": pairing_qr_png_data_uri(payload),
        "message": (
            f"Pairing code {pairing['code']} (expires {pairing['expires_at']}). "
            "Scan the QR in the companion app, or enter the code there. "
            "Do not dig through Settings to finish this."
        ),
    }


def confirm_pairing_payload(
    *,
    pairing_id: str,
    code: str,
    device_name: str,
    platform: str = "ios",
) -> dict[str, Any]:
    result = get_companion_store().confirm_pairing(
        pairing_id,
        code=code.upper(),
        device_name=device_name,
        platform=platform,
    )
    if result is None:
        return {"ok": False, "error": "Invalid or expired pairing code"}
    # Token is one-time; include once but warn never to speak it
    return {
        "ok": True,
        "device": result.get("device"),
        "token_once": result.get("token"),
        "message": (
            "Device paired. Deliver token_once to the device channel only; "
            "never repeat it in voice."
        ),
    }


def remove_device_payload(device_id: str) -> dict[str, Any]:
    ok = get_companion_store().unpair(device_id)
    if not ok:
        return {"ok": False, "error": f"Device not found: {device_id}"}
    return {"ok": True, "removed": True, "device_id": device_id}
