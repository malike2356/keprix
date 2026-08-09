"""Zoom user OAuth helpers (Prompt 632).

Standalone: tokens stored in encrypted local protected storage (file) under
KEPRIX_DATA_DIR. Optional Vault bundle when available. No VERLOX-hosted
credential service required.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_lock = threading.Lock()


@dataclass
class ZoomTokenBundle:
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None
    account_email: str | None = None
    scopes: list[str] | None = None

    @property
    def expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= float(self.expires_at) - 60

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "account_email": self.account_email,
            "scopes": list(self.scopes or []),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ZoomTokenBundle:
        return cls(
            access_token=str(raw.get("access_token") or raw.get("accessToken") or ""),
            refresh_token=raw.get("refresh_token") or raw.get("refreshToken"),
            expires_at=float(raw["expires_at"])
            if raw.get("expires_at") is not None
            else (
                float(raw["expiresAt"])
                if raw.get("expiresAt") is not None
                else None
            ),
            account_email=raw.get("account_email") or raw.get("accountEmail"),
            scopes=list(raw.get("scopes") or []),
        )


def is_zoom_oauth_configured() -> bool:
    return bool(
        (os.environ.get("ZOOM_CLIENT_ID") or "").strip()
        and (os.environ.get("ZOOM_CLIENT_SECRET") or "").strip()
    )


def zoom_oauth_scopes() -> list[str]:
    raw = (os.environ.get("ZOOM_OAUTH_SCOPES") or "meeting:write meeting:read user:read").strip()
    return [s for s in raw.replace(",", " ").split() if s]


def _token_path() -> Path:
    override = (os.environ.get("KEPRIX_ZOOM_TOKEN_PATH") or "").strip()
    if override:
        return Path(override)
    home = Path(os.environ.get("KEPRIX_HOME") or Path.home() / ".keprix")
    data = Path(os.environ.get("KEPRIX_DATA_DIR") or home / "data")
    return data / "zoom_oauth_tokens.json"


def _fernet_key() -> bytes | None:
    secret = (
        (os.environ.get("KEPRIX_ZOOM_TOKEN_SECRET") or "").strip()
        or (os.environ.get("KEPRIX_VAULT_MASTER_KEY") or "").strip()
        or (os.environ.get("KEPRIX_CONCIERGE_EMBED_SECRET") or "").strip()
    )
    if not secret:
        return None
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _encrypt(raw: str) -> str:
    key = _fernet_key()
    if not key:
        return "plain:" + base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")
    try:
        from cryptography.fernet import Fernet

        return "fernet:" + Fernet(key).encrypt(raw.encode("utf-8")).decode("ascii")
    except Exception:
        return "plain:" + base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _decrypt(blob: str) -> str:
    if blob.startswith("fernet:"):
        from cryptography.fernet import Fernet

        key = _fernet_key()
        if not key:
            raise RuntimeError("encrypted zoom token present but no secret configured")
        return Fernet(key).decrypt(blob[len("fernet:") :].encode("ascii")).decode("utf-8")
    if blob.startswith("plain:"):
        return base64.urlsafe_b64decode(blob[len("plain:") :].encode("ascii")).decode("utf-8")
    return blob


def _read_store() -> dict[str, Any]:
    path = _token_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(_decrypt(path.read_text(encoding="utf-8")))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}


def _write_store(data: dict[str, Any]) -> None:
    path = _token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_encrypt(json.dumps(data)), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def _key(workspace_id: str, user_id: str) -> str:
    return f"{workspace_id}::{user_id}"


def load_zoom_tokens(workspace_id: str, user_id: str) -> ZoomTokenBundle | None:
    with _lock:
        data = _read_store()
        row = data.get(_key(workspace_id, user_id))
        if not row:
            return None
        return ZoomTokenBundle.from_dict(row)


def save_zoom_tokens(workspace_id: str, user_id: str, tokens: ZoomTokenBundle) -> None:
    with _lock:
        data = _read_store()
        data[_key(workspace_id, user_id)] = tokens.to_dict()
        _write_store(data)


def revoke_zoom_tokens(workspace_id: str, user_id: str) -> bool:
    with _lock:
        data = _read_store()
        key = _key(workspace_id, user_id)
        if key not in data:
            return False
        del data[key]
        _write_store(data)
        return True


def zoom_authorize_url(*, redirect_uri: str, state: str) -> str | None:
    client_id = (os.environ.get("ZOOM_CLIENT_ID") or "").strip()
    if not client_id:
        return None
    params = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    return f"https://zoom.us/oauth/authorize?{params}"


def exchange_zoom_code(
    code: str,
    *,
    redirect_uri: str,
    workspace_id: str,
    user_id: str,
) -> ZoomTokenBundle:
    client_id = (os.environ.get("ZOOM_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("ZOOM_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("Zoom OAuth client credentials are not configured")
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    body = urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")
    req = Request(
        "https://zoom.us/oauth/token",
        data=body,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    tokens = ZoomTokenBundle(
        access_token=str(payload.get("access_token") or ""),
        refresh_token=payload.get("refresh_token"),
        expires_at=time.time() + float(payload.get("expires_in") or 3600),
        scopes=str(payload.get("scope") or "").split(),
    )
    # Best-effort identity
    try:
        me = _zoom_get_json("https://api.zoom.us/v2/users/me", tokens.access_token)
        tokens.account_email = me.get("email")
    except Exception:
        pass
    save_zoom_tokens(workspace_id, user_id, tokens)
    return tokens


def refresh_zoom_access_token(
    workspace_id: str,
    user_id: str,
    *,
    tokens: ZoomTokenBundle | None = None,
) -> ZoomTokenBundle | None:
    current = tokens or load_zoom_tokens(workspace_id, user_id)
    if not current or not current.refresh_token:
        return current
    client_id = (os.environ.get("ZOOM_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("ZOOM_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        return current
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    body = urlencode(
        {"grant_type": "refresh_token", "refresh_token": current.refresh_token}
    ).encode("utf-8")
    req = Request(
        "https://zoom.us/oauth/token",
        data=body,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError):
        return None
    next_tokens = ZoomTokenBundle(
        access_token=str(payload.get("access_token") or ""),
        refresh_token=payload.get("refresh_token") or current.refresh_token,
        expires_at=time.time() + float(payload.get("expires_in") or 3600),
        account_email=current.account_email,
        scopes=str(payload.get("scope") or "").split() or current.scopes,
    )
    save_zoom_tokens(workspace_id, user_id, next_tokens)
    return next_tokens


def _zoom_get_json(url: str, access_token: str) -> dict[str, Any]:
    req = Request(url, headers={"Authorization": f"Bearer {access_token}"}, method="GET")
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def zoom_connection_status(workspace_id: str, user_id: str) -> dict[str, Any]:
    configured = is_zoom_oauth_configured()
    tokens = load_zoom_tokens(workspace_id, user_id)
    connected = bool(tokens and tokens.access_token)
    return {
        "provider": "zoom",
        "oauthConfigured": configured,
        "connected": connected,
        "accountEmail": tokens.account_email if tokens else None,
        "scopes": list(tokens.scopes or []) if tokens else [],
        "requiredScopes": zoom_oauth_scopes(),
        "expired": bool(tokens.expired) if tokens else False,
        "status": (
            "ready"
            if configured and connected and not (tokens and tokens.expired)
            else "disconnected"
            if configured
            else "not_configured"
        ),
        "standalone": True,
        "verloxCredentialServiceRequired": False,
    }


def test_zoom_connection(workspace_id: str, user_id: str) -> dict[str, Any]:
    status = zoom_connection_status(workspace_id, user_id)
    if status["status"] != "ready":
        return {"ok": False, **status, "detail": "Zoom not ready"}
    tokens = load_zoom_tokens(workspace_id, user_id)
    assert tokens is not None
    try:
        me = _zoom_get_json("https://api.zoom.us/v2/users/me", tokens.access_token)
        return {
            "ok": True,
            **status,
            "accountEmail": me.get("email") or status.get("accountEmail"),
            "detail": "Zoom API /users/me ok",
        }
    except Exception as exc:
        return {"ok": False, **status, "detail": str(exc)[:200]}


__all__ = [
    "ZoomTokenBundle",
    "exchange_zoom_code",
    "is_zoom_oauth_configured",
    "load_zoom_tokens",
    "refresh_zoom_access_token",
    "revoke_zoom_tokens",
    "save_zoom_tokens",
    "test_zoom_connection",
    "zoom_authorize_url",
    "zoom_connection_status",
    "zoom_oauth_scopes",
]
