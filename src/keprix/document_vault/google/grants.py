"""Encrypted per-workspace Google Drive OAuth grants (Prompt 649).

Tokens never appear in public API payloads. Ciphertext is stored on the
Document Vault drive connection row. Local CE works without Google when
no grant exists (not_configured).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("cryptography package required for Drive grant encryption") from exc

    raw = (
        os.environ.get("KEPRIX_DOCUMENT_VAULT_GOOGLE_TOKEN_KEY")
        or os.environ.get("KEPRIX_VAULT_MASTER_KEY")
        or os.environ.get("KEPRIX_SECRET_KEY")
        or "keprix-local-dev-document-vault-google-key"
    ).encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


@dataclass
class DriveGrant:
    """In-memory grant; never serialize raw tokens to logs or public JSON."""

    access_token: str
    refresh_token: str = ""
    expires_at: str | None = None
    account_email: str | None = None
    scopes: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=_utcnow)

    def public_dict(self) -> dict[str, Any]:
        return {
            "connected": True,
            "account_email": self.account_email,
            "scopes": list(self.scopes),
            "expires_at": self.expires_at,
            "updated_at": self.updated_at,
        }

    def to_secret_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "account_email": self.account_email,
            "scopes": list(self.scopes),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_secret_dict(cls, data: dict[str, Any]) -> "DriveGrant":
        return cls(
            access_token=str(data.get("access_token") or ""),
            refresh_token=str(data.get("refresh_token") or ""),
            expires_at=data.get("expires_at"),
            account_email=data.get("account_email"),
            scopes=[str(s) for s in data.get("scopes") or []],
            updated_at=str(data.get("updated_at") or _utcnow()),
        )


def encrypt_grant(grant: DriveGrant) -> str:
    payload = json.dumps(grant.to_secret_dict(), sort_keys=True).encode("utf-8")
    return _fernet().encrypt(payload).decode("ascii")


def decrypt_grant(ciphertext: str) -> DriveGrant:
    raw = _fernet().decrypt(ciphertext.encode("ascii"))
    data = json.loads(raw.decode("utf-8"))
    return DriveGrant.from_secret_dict(data)


def new_verification_token() -> tuple[str, str]:
    """Return (plaintext token for Google channel, sha256 hex for storage)."""
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, digest


def verify_channel_token(plaintext: str, stored_hash: str) -> bool:
    if not plaintext or not stored_hash:
        return False
    digest = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    return secrets.compare_digest(digest, stored_hash)


def redact_mapping(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip secrets from any nested status/debug payload."""
    banned = {
        "access_token",
        "refresh_token",
        "grant_ciphertext",
        "client_secret",
        "verification_token",
        "token",
        "Authorization",
    }
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key in banned:
            continue
        if isinstance(value, dict):
            out[key] = redact_mapping(value)
        else:
            out[key] = value
    return out


__all__ = [
    "DriveGrant",
    "decrypt_grant",
    "encrypt_grant",
    "new_verification_token",
    "redact_mapping",
    "verify_channel_token",
]
