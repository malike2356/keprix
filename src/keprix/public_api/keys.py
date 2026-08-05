"""API key storage with hashed secrets at rest."""

from __future__ import annotations

import json
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import bcrypt

from keprix.public_api.schemas import (
    ApiKeyRecord,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    UpdateApiKeyRequest,
)
from keprix.public_api.scopes_catalog import (
    DEFAULT_ALLOWED_ENDPOINTS,
    DEFAULT_ALLOWED_MODELS,
    default_permissions,
    permissions_to_endpoints,
    permissions_to_scopes,
)


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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


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
    permissions: dict[str, str] = field(default_factory=dict)
    restrict_key: bool = True
    allowed_ips: list[str] = field(default_factory=list)
    auto_disable_if_leaked: bool = True
    enabled: bool = True
    expires_at: str | None = None
    key_prefix: str = ""


class ApiKeyStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _keys_file()

    def _load(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self, rows: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def _resolve_permissions(self, body: CreateApiKeyRequest) -> dict[str, str]:
        if body.permissions:
            base = default_permissions()
            base.update({k: str(v) for k, v in body.permissions.items()})
            return base
        if body.restrict_key:
            return default_permissions()
        # Unrestricted key: mark catalog items as write/access where available.
        perms = default_permissions()
        from keprix.public_api.scopes_catalog import SCOPE_CATALOG

        for group in SCOPE_CATALOG:
            for item in group["items"]:
                modes = item.get("modes") or ["none", "access"]
                if "write" in modes:
                    perms[item["id"]] = "write"
                elif "access" in modes:
                    perms[item["id"]] = "access"
        return perms

    def _resolve_endpoints(self, body: CreateApiKeyRequest, permissions: dict[str, str]) -> list[str]:
        if body.allowed_endpoints is not None:
            return list(body.allowed_endpoints)
        if not body.restrict_key:
            return []
        derived = permissions_to_endpoints(permissions)
        return derived or list(DEFAULT_ALLOWED_ENDPOINTS)

    def _resolve_models(self, body: CreateApiKeyRequest) -> list[str]:
        if body.allowed_models is not None:
            return list(body.allowed_models)
        if not body.restrict_key:
            return []
        return list(DEFAULT_ALLOWED_MODELS)

    def _resolve_expiry(self, body: CreateApiKeyRequest) -> str | None:
        if body.expires_at:
            return body.expires_at
        if body.expire_after_days:
            return _isoformat(_utcnow() + timedelta(days=int(body.expire_after_days)))
        return None

    def create(self, body: CreateApiKeyRequest) -> CreateApiKeyResponse:
        raw = f"kp_{secrets.token_urlsafe(32)}"
        key_id = str(uuid.uuid4())
        now = _isoformat(_utcnow())
        permissions = self._resolve_permissions(body)
        endpoints = self._resolve_endpoints(body, permissions)
        models = self._resolve_models(body)
        scopes = dict(body.scopes or {})
        scopes.update(permissions_to_scopes(permissions))
        if permissions.get("v1.tools") not in {"none", "", None}:
            scopes["tools:execute"] = True

        row = {
            "id": key_id,
            "name": body.name,
            "key_prefix": raw[:12],
            "key_hash": _hash_key(raw),
            "workspace_id": body.workspace_id,
            "role": body.role or "api",
            "scopes": scopes,
            "permissions": permissions,
            "allowed_models": models,
            "allowed_endpoints": endpoints,
            "monthly_limit": body.monthly_limit,
            "usage_this_month": 0,
            "created_at": now,
            "revoked_at": None,
            "enabled": bool(body.enabled),
            "restrict_key": bool(body.restrict_key),
            "expires_at": self._resolve_expiry(body),
            "allowed_ips": list(body.allowed_ips or []),
            "auto_disable_if_leaked": bool(body.auto_disable_if_leaked),
        }
        rows = self._load()
        rows.append(row)
        self._save(rows)
        record = self._to_record(row)
        return CreateApiKeyResponse(**record.model_dump(), secret=raw)

    def update(self, key_id: str, body: UpdateApiKeyRequest) -> ApiKeyRecord | None:
        rows = self._load()
        for row in rows:
            if row["id"] != key_id:
                continue
            if body.name is not None:
                row["name"] = body.name
            if body.permissions is not None:
                perms = default_permissions()
                perms.update({k: str(v) for k, v in body.permissions.items()})
                row["permissions"] = perms
                row["scopes"] = permissions_to_scopes(perms)
                if perms.get("v1.tools") not in {"none", "", None}:
                    row["scopes"]["tools:execute"] = True
                if body.allowed_endpoints is None and row.get("restrict_key", True):
                    row["allowed_endpoints"] = permissions_to_endpoints(perms)
            if body.scopes is not None:
                merged = dict(row.get("scopes") or {})
                merged.update(body.scopes)
                row["scopes"] = merged
            if body.allowed_models is not None:
                row["allowed_models"] = list(body.allowed_models)
            if body.allowed_endpoints is not None:
                row["allowed_endpoints"] = list(body.allowed_endpoints)
            if body.monthly_limit is not None:
                row["monthly_limit"] = body.monthly_limit
            if body.restrict_key is not None:
                row["restrict_key"] = bool(body.restrict_key)
            if body.clear_expiry:
                row["expires_at"] = None
            elif body.expires_at is not None:
                row["expires_at"] = body.expires_at
            elif body.expire_after_days is not None:
                row["expires_at"] = _isoformat(_utcnow() + timedelta(days=int(body.expire_after_days)))
            if body.allowed_ips is not None:
                row["allowed_ips"] = list(body.allowed_ips)
            if body.auto_disable_if_leaked is not None:
                row["auto_disable_if_leaked"] = bool(body.auto_disable_if_leaked)
            if body.enabled is not None:
                row["enabled"] = bool(body.enabled)
            self._save(rows)
            return self._to_record(row)
        return None

    def list_keys(self, workspace_id: str | None = None) -> list[ApiKeyRecord]:
        rows = self._load()
        result: list[ApiKeyRecord] = []
        for row in rows:
            if workspace_id and row.get("workspace_id") != workspace_id:
                continue
            result.append(self._to_record(row))
        return result

    def get(self, key_id: str) -> ApiKeyRecord | None:
        for row in self._load():
            if row["id"] == key_id:
                return self._to_record(row)
        return None

    def revoke(self, key_id: str) -> bool:
        rows = self._load()
        updated = False
        for row in rows:
            if row["id"] == key_id and not row.get("revoked_at"):
                row["revoked_at"] = _isoformat(_utcnow())
                row["enabled"] = False
                updated = True
        if updated:
            self._save(rows)
        return updated

    def set_enabled(self, key_id: str, enabled: bool) -> bool:
        rows = self._load()
        for row in rows:
            if row["id"] == key_id and not row.get("revoked_at"):
                row["enabled"] = bool(enabled)
                self._save(rows)
                return True
        return False

    def disable_if_leaked(self, key_id: str, *, reason: str = "leaked") -> bool:
        rows = self._load()
        for row in rows:
            if row["id"] != key_id:
                continue
            if not row.get("auto_disable_if_leaked", True):
                return False
            row["enabled"] = False
            row["leaked_disabled_at"] = _isoformat(_utcnow())
            row["leaked_reason"] = reason
            self._save(rows)
            return True
        return False

    def authenticate(self, raw_key: str) -> ApiKeyContext | None:
        if not raw_key:
            return None
        prefix = raw_key[:12] if len(raw_key) >= 12 else raw_key
        candidates = [row for row in self._load() if not row.get("revoked_at")]
        # Prefer prefix match to avoid bcrypt against every key (DoS).
        prefixed = [row for row in candidates if row.get("key_prefix") == prefix]
        search = prefixed or candidates
        for row in search:
            if not _verify_key(raw_key, row["key_hash"]):
                continue
            if not row.get("enabled", True):
                return None
            expires = _parse_iso(row.get("expires_at"))
            if expires and expires <= _utcnow():
                return None
            permissions = dict(row.get("permissions") or {})
            if not permissions and row.get("restrict_key", False):
                permissions = default_permissions()
            scopes = dict(row.get("scopes") or {})
            return ApiKeyContext(
                key_id=row["id"],
                workspace_id=row.get("workspace_id", "default"),
                role=row.get("role", "api"),
                allowed_models=list(row.get("allowed_models") or []),
                allowed_endpoints=list(row.get("allowed_endpoints") or []),
                monthly_limit=row.get("monthly_limit"),
                usage_this_month=int(row.get("usage_this_month") or 0),
                scopes=scopes,
                permissions=permissions,
                # Legacy rows without restrict_key stay unrestricted.
                restrict_key=bool(row["restrict_key"]) if "restrict_key" in row else False,
                allowed_ips=list(row.get("allowed_ips") or []),
                auto_disable_if_leaked=bool(row.get("auto_disable_if_leaked", True)),
                enabled=bool(row.get("enabled", True)),
                expires_at=row.get("expires_at"),
                key_prefix=str(row.get("key_prefix") or ""),
            )
        return None

    def increment_usage(self, key_id: str, amount: int = 1) -> None:
        rows = self._load()
        for row in rows:
            if row["id"] == key_id:
                row["usage_this_month"] = int(row.get("usage_this_month") or 0) + amount
        self._save(rows)

    def _to_record(self, row: dict[str, Any]) -> ApiKeyRecord:
        prefix = str(row.get("key_prefix") or "")
        masked = f"{'*' * 20}{prefix[-4:]}" if len(prefix) >= 4 else ("*" * 20)
        restrict = bool(row["restrict_key"]) if "restrict_key" in row else False
        return ApiKeyRecord(
            id=row["id"],
            name=row["name"],
            key_prefix=prefix,
            workspace_id=row.get("workspace_id", "default"),
            role=row.get("role", "api"),
            allowed_models=list(row.get("allowed_models") or []),
            allowed_endpoints=list(row.get("allowed_endpoints") or []),
            monthly_limit=row.get("monthly_limit"),
            usage_this_month=int(row.get("usage_this_month") or 0),
            created_at=row.get("created_at", ""),
            revoked=bool(row.get("revoked_at")),
            enabled=bool(row.get("enabled", True)),
            restrict_key=restrict,
            permissions=dict(row.get("permissions") or {}),
            scopes=dict(row.get("scopes") or {}),
            expires_at=row.get("expires_at"),
            allowed_ips=list(row.get("allowed_ips") or []),
            auto_disable_if_leaked=bool(row.get("auto_disable_if_leaked", True)),
            masked_key=masked,
        )


_store: ApiKeyStore | None = None


def get_api_key_store() -> ApiKeyStore:
    global _store
    if _store is None:
        _store = ApiKeyStore()
    return _store
