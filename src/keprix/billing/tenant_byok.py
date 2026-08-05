"""Per-tenant BYOK provider key vaulting via AES-GCM (never echo secrets)."""

from __future__ import annotations

import base64
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.security.crypto import decrypt_aes_gcm, derive_key, encrypt_aes_gcm


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "byok"
    except Exception:
        root = Path.home() / ".keprix" / "byok"
    root.mkdir(parents=True, exist_ok=True)
    return root / "tenant_keys.json"


def _master_key() -> bytes:
    secret = os.environ.get("KEPRIX_BYOK_MASTER") or os.environ.get("KEPRIX_BYOK_SALT") or "keprix-local-byok"
    salt = (os.environ.get("KEPRIX_BYOK_SALT_BYTES") or "keprix-byok-salt").encode("utf-8")[:16].ljust(16, b"0")
    return derive_key(secret, salt)


class TenantByokStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _path()
        self._lock = threading.RLock()
        self._rows: dict[str, dict[str, Any]] = {}
        if self._path.exists():
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            self._rows = {str(k): v for k, v in (payload.get("keys") or {}).items()}

    def _key(self, tenant_id: str, provider: str) -> str:
        return f"{tenant_id}:{provider}"

    def _save(self) -> None:
        self._path.write_text(json.dumps({"keys": self._rows}, indent=2), encoding="utf-8")

    def put(self, *, tenant_id: str, provider: str, api_key: str) -> dict[str, Any]:
        if not api_key.strip():
            raise ValueError("api_key required")
        raw = api_key.strip()
        encrypted = encrypt_aes_gcm(raw.encode("utf-8"), _master_key())
        entry = {
            "tenant_id": tenant_id,
            "provider": provider,
            "api_key_enc": base64.urlsafe_b64encode(encrypted).decode("ascii"),
            "cipher": "aes-gcm",
            "hint": f"...{raw[-4:]}" if len(raw) >= 4 else "****",
            "updated_at": _utcnow(),
        }
        with self._lock:
            self._rows[self._key(tenant_id, provider)] = entry
            self._save()
        return {"tenant_id": tenant_id, "provider": provider, "hint": entry["hint"], "cipher": "aes-gcm"}

    def get_secret(self, *, tenant_id: str, provider: str) -> str | None:
        row = self._rows.get(self._key(tenant_id, provider))
        if not row:
            return None
        blob = base64.urlsafe_b64decode(str(row["api_key_enc"]).encode("ascii"))
        return decrypt_aes_gcm(blob, _master_key()).decode("utf-8")

    def public_status(self, *, tenant_id: str) -> list[dict[str, Any]]:
        out = []
        for row in self._rows.values():
            if row.get("tenant_id") == tenant_id:
                out.append(
                    {
                        "provider": row.get("provider"),
                        "hint": row.get("hint"),
                        "cipher": row.get("cipher") or "legacy",
                        "updated_at": row.get("updated_at"),
                    }
                )
        return out


_byok: TenantByokStore | None = None


def get_byok_store(path: Path | None = None) -> TenantByokStore:
    global _byok
    if path is not None:
        return TenantByokStore(path=path)
    if _byok is None:
        _byok = TenantByokStore()
    return _byok
