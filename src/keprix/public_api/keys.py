"""API key storage with hashed secrets at rest."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import bcrypt

from keprix.public_api.schemas import ApiKeyRecord, CreateApiKeyRequest, CreateApiKeyResponse


def _keys_file() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home()) / "developer" / "api_keys.json"
    except Exception:
        return Path.home() / ".keprix" / "developer" / "api_keys.json"


def _hash_key(raw_key: str) -> str:
    return bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_key(raw_key: str, key_hash: str) -> bool:
    try:
        return bcrypt.checkpw(raw_key.encode("utf-8"), key_hash.encode("utf-8"))
    except Exception:
        return False


@dataclass
class ApiKeyContext:
    key_id: str
    workspace_id: str
    role: str
    allowed_models: list[str]
    allowed_endpoints: list[str]
    monthly_limit: int | None
    usage_this_month: int
    scopes: dict[str, Any]


class ApiKeyStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _keys_file()

    def _load(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self, rows: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def create(self, body: CreateApiKeyRequest) -> CreateApiKeyResponse:
        raw = f"kp_{secrets.token_urlsafe(32)}"
        key_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": key_id,
            "name": body.name,
            "key_prefix": raw[:12],
            "key_hash": _hash_key(raw),
            "workspace_id": body.workspace_id,
            "role": body.role,
            "scopes": body.scopes,
            "allowed_models": body.allowed_models,
            "allowed_endpoints": body.allowed_endpoints,
            "monthly_limit": body.monthly_limit,
            "usage_this_month": 0,
            "created_at": now,
            "revoked_at": None,
        }
        rows = self._load()
        rows.append(row)
        self._save(rows)
        record = self._to_record(row)
        return CreateApiKeyResponse(**record.model_dump(), secret=raw)

    def list_keys(self, workspace_id: str | None = None) -> list[ApiKeyRecord]:
        rows = self._load()
        result: list[ApiKeyRecord] = []
        for row in rows:
            if workspace_id and row.get("workspace_id") != workspace_id:
                continue
            result.append(self._to_record(row))
        return result

    def revoke(self, key_id: str) -> bool:
        rows = self._load()
        updated = False
        for row in rows:
            if row["id"] == key_id and not row.get("revoked_at"):
                row["revoked_at"] = datetime.now(timezone.utc).isoformat()
                updated = True
        if updated:
            self._save(rows)
        return updated

    def authenticate(self, raw_key: str) -> ApiKeyContext | None:
        if not raw_key:
            return None
        for row in self._load():
            if row.get("revoked_at"):
                continue
            if _verify_key(raw_key, row["key_hash"]):
                return ApiKeyContext(
                    key_id=row["id"],
                    workspace_id=row.get("workspace_id", "default"),
                    role=row.get("role", "developer"),
                    allowed_models=list(row.get("allowed_models") or []),
                    allowed_endpoints=list(row.get("allowed_endpoints") or []),
                    monthly_limit=row.get("monthly_limit"),
                    usage_this_month=int(row.get("usage_this_month") or 0),
                    scopes=dict(row.get("scopes") or {}),
                )
        return None

    def increment_usage(self, key_id: str, amount: int = 1) -> None:
        rows = self._load()
        for row in rows:
            if row["id"] == key_id:
                row["usage_this_month"] = int(row.get("usage_this_month") or 0) + amount
        self._save(rows)

    def _to_record(self, row: dict[str, Any]) -> ApiKeyRecord:
        return ApiKeyRecord(
            id=row["id"],
            name=row["name"],
            key_prefix=row["key_prefix"],
            workspace_id=row.get("workspace_id", "default"),
            role=row.get("role", "developer"),
            allowed_models=list(row.get("allowed_models") or []),
            allowed_endpoints=list(row.get("allowed_endpoints") or []),
            monthly_limit=row.get("monthly_limit"),
            usage_this_month=int(row.get("usage_this_month") or 0),
            created_at=row.get("created_at", ""),
            revoked=bool(row.get("revoked_at")),
        )


_store: ApiKeyStore | None = None


def get_api_key_store() -> ApiKeyStore:
    global _store
    if _store is None:
        _store = ApiKeyStore()
    return _store


def fingerprint_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
