"""Session management with Redis or in-memory fallback."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

import bcrypt
import pyotp

from keprix.config.settings import get_settings
from keprix.security.audit import hash_ip

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore[assignment]


@dataclass
class SessionRecord:
    session_id: str
    user_id: str
    created_at: float
    last_seen: float
    ip_hash: str
    user_agent_hash: str


class SessionStore:
    def __init__(self) -> None:
        settings = get_settings()
        self._ttl_seconds = settings.session_ttl_days * 86400
        self._memory: dict[str, dict[str, Any]] = {}
        self._redis = None
        if settings.redis_url and redis is not None:
            try:
                self._redis = redis.from_url(settings.redis_url, decode_responses=True)
            except Exception:
                self._redis = None

    def _session_key(self, token_hash: str) -> str:
        return f"session:{token_hash}"

    def create_session(
        self,
        user_id: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, SessionRecord]:
        raw_token = secrets.token_bytes(32)
        token = raw_token.hex()
        token_hash = hashlib.sha256(raw_token).hexdigest()
        now = time.time()
        record = SessionRecord(
            session_id=token_hash[:16],
            user_id=user_id,
            created_at=now,
            last_seen=now,
            ip_hash=hash_ip(ip or ""),
            user_agent_hash=hashlib.sha256((user_agent or "").encode("utf-8")).hexdigest(),
        )
        payload = {
            "session_id": record.session_id,
            "user_id": record.user_id,
            "created_at": record.created_at,
            "last_seen": record.last_seen,
            "ip_hash": record.ip_hash,
            "user_agent_hash": record.user_agent_hash,
        }
        key = self._session_key(token_hash)
        if self._redis is not None:
            self._redis.set(key, json.dumps(payload), ex=self._ttl_seconds)
        else:
            self._memory[key] = payload
        return token, record

    def get_session(self, token: str) -> SessionRecord | None:
        token_hash = hashlib.sha256(bytes.fromhex(token)).hexdigest() if len(token) == 64 else hashlib.sha256(token.encode("utf-8")).hexdigest()
        key = self._session_key(token_hash)
        raw = self._redis.get(key) if self._redis is not None else self._memory.get(key)
        if not raw:
            return None
        data = json.loads(raw) if isinstance(raw, str) else raw
        return SessionRecord(
            session_id=data["session_id"],
            user_id=data["user_id"],
            created_at=float(data["created_at"]),
            last_seen=float(data["last_seen"]),
            ip_hash=data["ip_hash"],
            user_agent_hash=data["user_agent_hash"],
        )

    def delete_session(self, token: str) -> None:
        token_hash = hashlib.sha256(bytes.fromhex(token)).hexdigest() if len(token) == 64 else hashlib.sha256(token.encode("utf-8")).hexdigest()
        key = self._session_key(token_hash)
        if self._redis is not None:
            self._redis.delete(key)
        else:
            self._memory.pop(key, None)

    def list_sessions(self, user_id: str) -> list[SessionRecord]:
        results: list[SessionRecord] = []
        if self._redis is not None:
            for key in self._redis.scan_iter("session:*"):
                raw = self._redis.get(key)
                if not raw:
                    continue
                data = json.loads(raw)
                if data.get("user_id") == user_id:
                    results.append(
                        SessionRecord(
                            session_id=data["session_id"],
                            user_id=data["user_id"],
                            created_at=float(data["created_at"]),
                            last_seen=float(data["last_seen"]),
                            ip_hash=data["ip_hash"],
                            user_agent_hash=data["user_agent_hash"],
                        )
                    )
            return results
        for payload in self._memory.values():
            if payload.get("user_id") == user_id:
                results.append(
                    SessionRecord(
                        session_id=payload["session_id"],
                        user_id=payload["user_id"],
                        created_at=float(payload["created_at"]),
                        last_seen=float(payload["last_seen"]),
                        ip_hash=payload["ip_hash"],
                        user_agent_hash=payload["user_agent_hash"],
                    )
                )
        return results


class TotpManager:
    def __init__(self, issuer: str = "Keprix") -> None:
        self.issuer = issuer

    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def provisioning_uri(self, secret: str, username: str) -> str:
        return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=self.issuer)

    def verify(self, secret: str, code: str) -> bool:
        return pyotp.TOTP(secret).verify(code, valid_window=1)


class BackupCodeManager:
    @staticmethod
    def generate_codes(count: int = 10) -> list[str]:
        return [secrets.token_hex(4) for _ in range(count)]

    @staticmethod
    def hash_codes(codes: list[str]) -> list[str]:
        return [bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt()).decode("utf-8") for code in codes]

    @staticmethod
    def verify_code(code: str, hashed_codes: list[str]) -> bool:
        return any(bcrypt.checkpw(code.encode("utf-8"), item.encode("utf-8")) for item in hashed_codes)


_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
