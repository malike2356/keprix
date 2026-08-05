"""Tenant ownership checks for stores and APIs."""

from __future__ import annotations

import os
from typing import Any

from keprix.security.isolation_violation import IsolationViolation
from keprix.tenancy.resolve import DEFAULT_TENANT_ID


class TenantIsolationError(IsolationViolation):
    """Cross-tenant access attempt."""

    def __init__(self, message: str = "Tenant isolation failure", *, tenant_id: str = "") -> None:
        super().__init__(message, product_id="keprix", workspace_id=tenant_id, table="tenant")
        self.tenant_id = tenant_id


def isolation_enabled() -> bool:
    return os.environ.get("KEPRIX_TENANT_ISOLATION", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def resource_tenant_id(resource: Any) -> str | None:
    if resource is None:
        return None
    if isinstance(resource, dict):
        value = resource.get("tenant_id")
        if value:
            return str(value)
        meta = resource.get("metadata") or {}
        if isinstance(meta, dict) and meta.get("tenant_id"):
            return str(meta["tenant_id"])
        return None
    value = getattr(resource, "tenant_id", None)
    if value:
        return str(value)
    meta = getattr(resource, "metadata", None)
    if isinstance(meta, dict) and meta.get("tenant_id"):
        return str(meta["tenant_id"])
    return None


def current_tenant_id(*, fallback: str = DEFAULT_TENANT_ID) -> str:
    try:
        from keprix.security.product_context import get_product_context_or_none

        ctx = get_product_context_or_none()
        if ctx and ctx.tenant_id:
            return str(ctx.tenant_id)
    except Exception:
        pass
    return os.environ.get("KEPRIX_TENANT_ID") or fallback


def assert_tenant_owns(resource: Any, *, tenant_id: str | None = None, soft_legacy: bool | None = None) -> None:
    """Fail closed when both sides declare a tenant and they differ.

    Legacy rows without tenant_id soft-pass unless KEPRIX_TENANT_ISOLATION_STRICT=1.
    """
    if not isolation_enabled():
        return
    expected = tenant_id or current_tenant_id()
    actual = resource_tenant_id(resource)
    if soft_legacy is None:
        soft_legacy = os.environ.get("KEPRIX_TENANT_ISOLATION_STRICT", "").lower() not in {
            "1",
            "true",
            "yes",
            "on",
        }
    if actual is None:
        if soft_legacy:
            return
        raise TenantIsolationError("Resource missing tenant_id", tenant_id=expected)
    if actual != expected:
        raise TenantIsolationError(
            f"Cross-tenant access: resource={actual} context={expected}",
            tenant_id=expected,
        )


def stamp_tenant(fields: dict[str, Any], *, tenant_id: str | None = None) -> dict[str, Any]:
    out = dict(fields)
    out.setdefault("tenant_id", tenant_id or current_tenant_id())
    return out
