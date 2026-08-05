"""Lightweight connection probes for conversational channel config."""

from __future__ import annotations

import asyncio
import socket
from typing import Any
from urllib.parse import urlparse

import httpx

from keprix.channels.channel_config_store import (
    get_decrypted_credentials,
    update_test_result,
)
from keprix.channels.channel_requirements import get_channel


async def _probe_telegram(credentials: dict[str, str]) -> tuple[bool, str, dict[str, Any]]:
    token = credentials.get("bot_token", "").strip()
    if not token:
        return False, "Missing bot_token", {}
    url = f"https://api.telegram.org/bot{token}/getMe"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        return False, f"Telegram API returned HTTP {resp.status_code}", {}
    data = resp.json()
    if not data.get("ok"):
        return False, str(data.get("description") or "Telegram getMe failed"), {}
    result = data.get("result") or {}
    username = result.get("username")
    meta = {"bot_username": f"@{username}" if username else None, "bot_id": result.get("id")}
    return True, "Telegram bot authenticated", meta


async def _probe_discord(credentials: dict[str, str]) -> tuple[bool, str, dict[str, Any]]:
    token = credentials.get("bot_token", "").strip()
    if not token:
        return False, "Missing bot_token", {}
    headers = {"Authorization": f"Bot {token}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get("https://discord.com/api/v10/users/@me", headers=headers)
    if resp.status_code != 200:
        return False, f"Discord API returned HTTP {resp.status_code}", {}
    data = resp.json()
    meta = {"bot_username": data.get("username"), "bot_id": data.get("id")}
    return True, "Discord bot authenticated", meta


async def _probe_slack(credentials: dict[str, str]) -> tuple[bool, str, dict[str, Any]]:
    token = credentials.get("bot_token", "").strip()
    if not token:
        return False, "Missing bot_token", {}
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post("https://slack.com/api/auth.test", headers=headers)
    data = resp.json()
    if not data.get("ok"):
        return False, str(data.get("error") or "Slack auth.test failed"), {}
    meta = {"team": data.get("team"), "user": data.get("user")}
    return True, "Slack bot authenticated", meta


def _tcp_probe(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


async def _probe_email(credentials: dict[str, str]) -> tuple[bool, str, dict[str, Any]]:
    imap_host = credentials.get("imap_host", "").strip()
    smtp_host = credentials.get("smtp_host", "").strip()
    imap_port = int(credentials.get("imap_port") or "993")
    smtp_port = int(credentials.get("smtp_port") or "587")
    notes: list[str] = []
    ok = True
    if imap_host:
        reachable = await asyncio.to_thread(_tcp_probe, imap_host, imap_port)
        if reachable:
            notes.append(f"IMAP {imap_host}:{imap_port} reachable")
        else:
            ok = False
            notes.append(f"IMAP {imap_host}:{imap_port} unreachable")
    if smtp_host:
        reachable = await asyncio.to_thread(_tcp_probe, smtp_host, smtp_port)
        if reachable:
            notes.append(f"SMTP {smtp_host}:{smtp_port} reachable")
        else:
            ok = False
            notes.append(f"SMTP {smtp_host}:{smtp_port} unreachable")
    if not notes:
        return True, "Email credentials saved; TCP probe skipped (no hosts)", {}
    return ok, "; ".join(notes), {}


async def _probe_sms(credentials: dict[str, str]) -> tuple[bool, str, dict[str, Any]]:
    sid = credentials.get("account_sid", "").strip()
    token = credentials.get("auth_token", "").strip()
    if not sid or not token:
        return False, "Missing Twilio credentials", {}
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, auth=(sid, token))
    if resp.status_code != 200:
        return False, f"Twilio API returned HTTP {resp.status_code}", {}
    return True, "Twilio account authenticated", {}


async def _probe_whatsapp_cloud(credentials: dict[str, str]) -> tuple[bool, str, dict[str, Any]]:
    token = credentials.get("access_token", "").strip()
    phone_id = credentials.get("phone_number_id", "").strip()
    if not token or not phone_id:
        return False, "Missing access_token or phone_number_id", {}
    url = f"https://graph.facebook.com/v20.0/{phone_id}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, params={"access_token": token, "fields": "id,display_phone_number,verified_name"})
    if resp.status_code != 200:
        return False, f"WhatsApp Cloud API returned HTTP {resp.status_code}", {}
    data = resp.json()
    meta = {
        "phone_number_id": data.get("id"),
        "display_phone_number": data.get("display_phone_number"),
        "verified_name": data.get("verified_name"),
    }
    return True, "WhatsApp Cloud phone number authenticated", meta


async def _probe_whatsapp(credentials: dict[str, str]) -> tuple[bool, str, dict[str, Any]]:
    enabled = (credentials.get("enabled") or "").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return False, "Set enabled=true to turn on the WhatsApp bridge", {}
    path = (credentials.get("credentials_path") or "").strip()
    if path:
        from pathlib import Path

        if not Path(path).expanduser().exists():
            return (
                True,
                "WhatsApp bridge enabled; credentials path not found yet (pair with `keprix whatsapp`)",
                {"needs_pairing": True},
            )
    return True, "WhatsApp bridge enabled; run `keprix whatsapp` to pair if needed", {"needs_pairing": True}


async def _probe_signal(credentials: dict[str, str]) -> tuple[bool, str, dict[str, Any]]:
    base = (credentials.get("http_url") or "").rstrip("/")
    account = (credentials.get("account") or "").strip()
    if not base or not account:
        return False, "Missing http_url or account", {}
    parsed = urlparse(base if "://" in base else f"http://{base}")
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if host and not await asyncio.to_thread(_tcp_probe, host, port):
        return False, f"signal-cli HTTP endpoint unreachable at {base}", {}
    # Best-effort about / accounts probe
    async with httpx.AsyncClient(timeout=10.0) as client:
        about = await client.get(f"{base}/v1/about")
        if about.status_code == 200:
            return True, "signal-cli HTTP API reachable", {"account": account}
        # Some builds expose accounts list
        accounts = await client.get(f"{base}/v1/accounts")
        if accounts.status_code == 200:
            return True, "signal-cli accounts endpoint reachable", {"account": account}
    return True, "signal-cli host reachable; account will be verified when the adapter connects", {"account": account}


async def _probe_matrix(credentials: dict[str, str]) -> tuple[bool, str, dict[str, Any]]:
    homeserver = (credentials.get("homeserver") or "").rstrip("/")
    if not homeserver:
        return False, "Missing homeserver", {}
    token = (credentials.get("access_token") or "").strip()
    user_id = (credentials.get("user_id") or "").strip()
    password = (credentials.get("password") or "").strip()
    async with httpx.AsyncClient(timeout=15.0) as client:
        if token:
            resp = await client.get(
                f"{homeserver}/_matrix/client/v3/account/whoami",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code != 200:
                return False, f"Matrix whoami returned HTTP {resp.status_code}", {}
            data = resp.json()
            return True, "Matrix access token authenticated", {"user_id": data.get("user_id")}
        if user_id and password:
            resp = await client.post(
                f"{homeserver}/_matrix/client/v3/login",
                json={"type": "m.login.password", "user": user_id, "password": password},
            )
            if resp.status_code != 200:
                return False, f"Matrix login returned HTTP {resp.status_code}", {}
            data = resp.json()
            return True, "Matrix password login succeeded", {"user_id": data.get("user_id")}
    return False, "Provide access_token or user_id+password", {}


async def _probe_teams(credentials: dict[str, str]) -> tuple[bool, str, dict[str, Any]]:
    client_id = (credentials.get("client_id") or "").strip()
    client_secret = (credentials.get("client_secret") or "").strip()
    tenant_id = (credentials.get("tenant_id") or "").strip()
    if not client_id or not client_secret or not tenant_id:
        return False, "Missing client_id, client_secret, or tenant_id", {}
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, data=data)
    if resp.status_code != 200:
        return False, f"Azure token endpoint returned HTTP {resp.status_code}", {}
    body = resp.json()
    if not body.get("access_token"):
        return False, "Azure token response missing access_token", {}
    return True, "Azure AD app credentials authenticated", {"token_type": body.get("token_type")}


_PROBES = {
    "telegram": _probe_telegram,
    "discord": _probe_discord,
    "slack": _probe_slack,
    "email": _probe_email,
    "sms": _probe_sms,
    "whatsapp_cloud": _probe_whatsapp_cloud,
    "whatsapp": _probe_whatsapp,
    "signal": _probe_signal,
    "matrix": _probe_matrix,
    "teams": _probe_teams,
}


def _redact(message: str, credentials: dict[str, str]) -> str:
    safe = message
    for value in credentials.values():
        if value and len(value) >= 8 and value in safe:
            safe = safe.replace(value, "[redacted]")
    return safe


async def test_channel(channel_id: str) -> dict[str, Any]:
    req = get_channel(channel_id)
    if req is None:
        return {"success": False, "message": f"Unknown channel: {channel_id}"}

    credentials = get_decrypted_credentials(req.id)
    if not credentials:
        return {"success": False, "message": f"{req.name} is not configured"}

    probe = _PROBES.get(req.id)
    if probe is None:
        return {
            "success": True,
            "message": f"{req.name} credentials are saved; live probe not implemented yet",
            "deferred": True,
        }

    try:
        success, message, meta = await probe(credentials)
    except Exception as exc:  # noqa: BLE001 - surface probe errors to the agent
        success, message, meta = False, f"Probe failed: {exc}", {}

    safe_message = _redact(message, credentials)

    try:
        update_test_result(req.id, success=success, message=safe_message, meta=meta or None)
    except ValueError:
        pass

    return {"success": success, "message": safe_message, "meta": meta or {}}
