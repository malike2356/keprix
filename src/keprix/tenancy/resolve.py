"""Resolve tenant_id for ProductContext."""

from __future__ import annotations

import os
from typing import Any

DEFAULT_TENANT_ID = "local"


def _host_subdomain(host: str | None) -> str | None:
    if not host:
        return None
    host = host.split(":")[0].strip().lower()
    parts = host.split(".")
    if len(parts) < 3:
        return None
    candidate = parts[0]
    if candidate in {"www", "api", "app", "localhost"}:
        return None
    return candidate


def resolve_tenant_id(
    *,
    header_ref: str | None = None,
    user: dict[str, Any] | None = None,
    host: str | None = None,
    env_default: str | None = None,
) -> str:
    """Resolve active tenant.

    Order:
    1. Explicit X-Keprix-Tenant (id or slug) when membership allows (or auth off)
    2. Optional subdomain when KEPRIX_TENANT_SUBDOMAIN enabled
    3. User default_tenant_id / first membership
    4. KEPRIX_TENANT_ID / local
    """
    from keprix.tenancy.store import get_tenant_store

    store = get_tenant_store()
    store.ensure_default()

    user_id = ""
    if user:
        user_id = str(user.get("id") or user.get("username") or "")

    ref = (header_ref or "").strip()
    if ref:
        tenant = store.resolve_ref(ref)
        if tenant and tenant.status == "active":
            if not user_id or store.user_has_membership(user_id, tenant.id) or tenant.id == DEFAULT_TENANT_ID:
                return tenant.id
            # Membership missing: still bind if single-tenant CE and slug/id is local
            if tenant.slug == DEFAULT_TENANT_ID:
                return tenant.id

    if os.environ.get("KEPRIX_TENANT_SUBDOMAIN", "").lower() in {"1", "true", "yes", "on"}:
        sub = _host_subdomain(host)
        if sub:
            tenant = store.get_by_slug(sub)
            if tenant and tenant.status == "active":
                return tenant.id

    if user:
        preferred = str(user.get("default_tenant_id") or user.get("tenant_id") or "").strip()
        if preferred:
            tenant = store.resolve_ref(preferred)
            if tenant and tenant.status == "active":
                if not user_id or store.user_has_membership(user_id, tenant.id) or tenant.id == DEFAULT_TENANT_ID:
                    return tenant.id
        if user_id:
            memberships = store.list_memberships(user_id=user_id)
            if memberships:
                return memberships[0].tenant_id

    fallback = (env_default or os.environ.get("KEPRIX_TENANT_ID") or DEFAULT_TENANT_ID).strip()
    tenant = store.resolve_ref(fallback)
    if tenant:
        return tenant.id
    return DEFAULT_TENANT_ID
