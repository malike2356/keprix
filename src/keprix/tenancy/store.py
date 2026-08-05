"""Tenant store: Postgres when available, JSON fallback (forced off under pytest)."""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

from keprix.tenancy.models import Membership, Tenant, _utcnow

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


class TenantConflictError(ValueError):
    pass


class TenantNotFoundError(LookupError):
    pass


def _use_db() -> bool:
    if "pytest" in sys.modules:
        return False
    if os.environ.get("KEPRIX_TENANCY_FORCE_JSON", "").lower() in {"1", "true", "yes", "on"}:
        return False
    try:
        from keprix.database import get_session_factory

        return get_session_factory() is not None
    except Exception:
        return False


def _store_path() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "tenancy"
    except Exception:
        root = Path(os.environ.get("KEPRIX_DATA_DIR") or Path.home() / ".keprix") / "tenancy"
    root.mkdir(parents=True, exist_ok=True)
    return root / "tenants.json"


def normalize_slug(slug: str) -> str:
    value = (slug or "").strip().lower().replace("_", "-").replace(" ", "-")
    if not _SLUG_RE.match(value):
        raise ValueError(f"Invalid tenant slug: {slug!r}")
    return value


class TenantStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _store_path()
        self._lock = threading.RLock()
        self._tenants: dict[str, Tenant] = {}
        self._memberships: list[Membership] = []
        self._load_json()

    def _load_json(self) -> None:
        if not self._path.exists():
            return
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        self._tenants = {
            str(row["id"]): Tenant.from_dict(row) for row in (payload.get("tenants") or [])
        }
        self._memberships = [
            Membership.from_dict(row) for row in (payload.get("memberships") or [])
        ]

    def _save_json(self) -> None:
        payload = {
            "tenants": [t.to_dict() for t in self._tenants.values()],
            "memberships": [m.to_dict() for m in self._memberships],
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def ensure_default(self, *, owner_user_id: str = "local") -> Tenant:
        existing = self.get_by_slug("local")
        if existing:
            return existing
        return self.create(
            slug="local",
            display_name="Local",
            owner_user_id=owner_user_id,
            tenant_id="local",
        )

    def create(
        self,
        *,
        slug: str,
        display_name: str,
        owner_user_id: str,
        tenant_id: str | None = None,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> Tenant:
        slug_norm = normalize_slug(slug)
        with self._lock:
            if self.get_by_slug(slug_norm) is not None:
                raise TenantConflictError(f"Tenant slug already exists: {slug_norm}")
            tid = tenant_id or str(uuid.uuid4())
            if tid in self._tenants:
                raise TenantConflictError(f"Tenant id already exists: {tid}")
            tenant = Tenant(
                id=tid,
                slug=slug_norm,
                display_name=(display_name or slug_norm).strip(),
                owner_user_id=str(owner_user_id),
                status=status,  # type: ignore[arg-type]
                metadata=dict(metadata or {}),
            )
            if _use_db():
                self._pg_insert(tenant)
            self._tenants[tenant.id] = tenant
            self._memberships.append(
                Membership(tenant_id=tenant.id, user_id=str(owner_user_id), role="owner")
            )
            self._save_json()
            return tenant

    def list_tenants(self) -> list[Tenant]:
        with self._lock:
            if _use_db():
                self._pg_refresh()
            return sorted(self._tenants.values(), key=lambda t: t.slug)

    def get(self, tenant_id: str) -> Tenant | None:
        with self._lock:
            if _use_db():
                row = self._pg_get(tenant_id)
                if row:
                    self._tenants[row.id] = row
                    return row
            return self._tenants.get(tenant_id)

    def get_by_slug(self, slug: str) -> Tenant | None:
        slug_norm = (slug or "").strip().lower()
        with self._lock:
            for tenant in self._tenants.values():
                if tenant.slug == slug_norm:
                    return tenant
            if _use_db():
                self._pg_refresh()
                for tenant in self._tenants.values():
                    if tenant.slug == slug_norm:
                        return tenant
        return None

    def update(self, tenant_id: str, **fields: Any) -> Tenant:
        with self._lock:
            tenant = self.get(tenant_id)
            if tenant is None:
                raise TenantNotFoundError(tenant_id)
            if "slug" in fields and fields["slug"] is not None:
                new_slug = normalize_slug(str(fields["slug"]))
                other = self.get_by_slug(new_slug)
                if other and other.id != tenant_id:
                    raise TenantConflictError(f"Tenant slug already exists: {new_slug}")
                tenant.slug = new_slug
            if "display_name" in fields and fields["display_name"] is not None:
                tenant.display_name = str(fields["display_name"]).strip()
            if "status" in fields and fields["status"] is not None:
                tenant.status = str(fields["status"])  # type: ignore[assignment]
            if "owner_user_id" in fields and fields["owner_user_id"] is not None:
                tenant.owner_user_id = str(fields["owner_user_id"])
            if "metadata" in fields and fields["metadata"] is not None:
                tenant.metadata = dict(fields["metadata"])
            tenant.updated_at = _utcnow().isoformat()
            if _use_db():
                self._pg_update(tenant)
            self._tenants[tenant.id] = tenant
            self._save_json()
            return tenant

    def add_membership(self, tenant_id: str, user_id: str, role: str = "member") -> Membership:
        if self.get(tenant_id) is None:
            raise TenantNotFoundError(tenant_id)
        with self._lock:
            for m in self._memberships:
                if m.tenant_id == tenant_id and m.user_id == user_id:
                    m.role = role  # type: ignore[assignment]
                    if _use_db():
                        self._pg_upsert_membership(m)
                    self._save_json()
                    return m
            membership = Membership(tenant_id=tenant_id, user_id=user_id, role=role)  # type: ignore[arg-type]
            self._memberships.append(membership)
            if _use_db():
                self._pg_upsert_membership(membership)
            self._save_json()
            return membership

    def list_memberships(self, *, tenant_id: str | None = None, user_id: str | None = None) -> list[Membership]:
        if _use_db():
            self._pg_refresh_memberships()
        rows = list(self._memberships)
        if tenant_id:
            rows = [m for m in rows if m.tenant_id == tenant_id]
        if user_id:
            rows = [m for m in rows if m.user_id == user_id]
        return rows

    def user_has_membership(self, user_id: str, tenant_id: str) -> bool:
        return any(m.tenant_id == tenant_id and m.user_id == user_id for m in self._memberships)

    def resolve_ref(self, ref: str) -> Tenant | None:
        ref = (ref or "").strip()
        if not ref:
            return None
        tenant = self.get(ref)
        if tenant:
            return tenant
        return self.get_by_slug(ref)

    # --- Postgres helpers (control_plane_tenants extended) ---

    def _pg_insert(self, tenant: Tenant) -> None:
        from sqlalchemy import text

        from keprix.database import get_session_factory

        factory = get_session_factory()
        if factory is None:
            return
        with factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO control_plane_tenants
                        (tenant_id, name, status, created_at, slug, display_name, owner_user_id)
                    VALUES
                        (:tenant_id, :name, :status, NOW(), :slug, :display_name, :owner_user_id)
                    ON CONFLICT (tenant_id) DO NOTHING
                    """
                ),
                {
                    "tenant_id": tenant.id,
                    "name": tenant.display_name,
                    "status": tenant.status,
                    "slug": tenant.slug,
                    "display_name": tenant.display_name,
                    "owner_user_id": tenant.owner_user_id,
                },
            )
            session.commit()

    def _pg_update(self, tenant: Tenant) -> None:
        from sqlalchemy import text

        from keprix.database import get_session_factory

        factory = get_session_factory()
        if factory is None:
            return
        with factory() as session:
            session.execute(
                text(
                    """
                    UPDATE control_plane_tenants
                    SET name = :name,
                        status = :status,
                        slug = :slug,
                        display_name = :display_name,
                        owner_user_id = :owner_user_id
                    WHERE tenant_id = :tenant_id
                    """
                ),
                {
                    "tenant_id": tenant.id,
                    "name": tenant.display_name,
                    "status": tenant.status,
                    "slug": tenant.slug,
                    "display_name": tenant.display_name,
                    "owner_user_id": tenant.owner_user_id,
                },
            )
            session.commit()

    def _pg_get(self, tenant_id: str) -> Tenant | None:
        from sqlalchemy import text

        from keprix.database import get_session_factory

        factory = get_session_factory()
        if factory is None:
            return None
        with factory() as session:
            row = session.execute(
                text(
                    """
                    SELECT tenant_id, COALESCE(display_name, name) AS display_name,
                           COALESCE(slug, tenant_id) AS slug,
                           COALESCE(owner_user_id, '') AS owner_user_id,
                           status, created_at
                    FROM control_plane_tenants
                    WHERE tenant_id = :tenant_id
                    """
                ),
                {"tenant_id": tenant_id},
            ).mappings().first()
        if not row:
            return None
        return Tenant(
            id=str(row["tenant_id"]),
            slug=str(row["slug"]),
            display_name=str(row["display_name"]),
            owner_user_id=str(row["owner_user_id"] or ""),
            status=str(row["status"] or "active"),  # type: ignore[arg-type]
            created_at=str(row["created_at"]),
        )

    def _pg_refresh(self) -> None:
        from sqlalchemy import text

        from keprix.database import get_session_factory

        factory = get_session_factory()
        if factory is None:
            return
        with factory() as session:
            rows = session.execute(
                text(
                    """
                    SELECT tenant_id, COALESCE(display_name, name) AS display_name,
                           COALESCE(slug, tenant_id) AS slug,
                           COALESCE(owner_user_id, '') AS owner_user_id,
                           status, created_at
                    FROM control_plane_tenants
                    """
                )
            ).mappings().all()
        for row in rows:
            tenant = Tenant(
                id=str(row["tenant_id"]),
                slug=str(row["slug"]),
                display_name=str(row["display_name"]),
                owner_user_id=str(row["owner_user_id"] or ""),
                status=str(row["status"] or "active"),  # type: ignore[arg-type]
                created_at=str(row["created_at"]),
            )
            self._tenants[tenant.id] = tenant


    def _pg_upsert_membership(self, membership: Membership) -> None:
        from sqlalchemy import text

        from keprix.database import get_session_factory

        factory = get_session_factory()
        if factory is None:
            return
        with factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO control_plane_memberships (tenant_id, user_id, role, created_at)
                    VALUES (:tenant_id, :user_id, :role, NOW())
                    ON CONFLICT (tenant_id, user_id) DO UPDATE SET role = EXCLUDED.role
                    """
                ),
                {
                    "tenant_id": membership.tenant_id,
                    "user_id": membership.user_id,
                    "role": membership.role,
                },
            )
            session.commit()

    def _pg_refresh_memberships(self) -> None:
        from sqlalchemy import text

        from keprix.database import get_session_factory

        factory = get_session_factory()
        if factory is None:
            return
        with factory() as session:
            rows = session.execute(
                text("SELECT tenant_id, user_id, role, created_at FROM control_plane_memberships")
            ).mappings().all()
        merged = {
            (m.tenant_id, m.user_id): m for m in self._memberships
        }
        for row in rows:
            membership = Membership(
                tenant_id=str(row["tenant_id"]),
                user_id=str(row["user_id"]),
                role=str(row["role"] or "member"),  # type: ignore[arg-type]
                created_at=str(row["created_at"]),
            )
            merged[(membership.tenant_id, membership.user_id)] = membership
        self._memberships = list(merged.values())


_store: TenantStore | None = None


def get_tenant_store() -> TenantStore:
    global _store
    if _store is None:
        _store = TenantStore()
        _store.ensure_default()
    return _store


def reset_tenant_store_for_tests(path: Path | None = None) -> TenantStore:
    global _store
    _store = TenantStore(path=path)
    return _store
