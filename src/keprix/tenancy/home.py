"""Request-scoped filesystem namespace for tenant-owned agent state."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from keprix_constants import (
    get_default_keprix_root,
    reset_keprix_home_override,
    set_keprix_home_override,
)

_TENANT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def tenant_home_isolation_enabled() -> bool:
    """Return whether tenant-owned files should use per-tenant homes."""
    return os.getenv("KEPRIX_TENANT_HOME_ISOLATION", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def tenant_home(tenant_id: str) -> Path:
    """Return a validated tenant home below the Keprix data root."""
    value = str(tenant_id or "").strip()
    if not _TENANT_ID.fullmatch(value):
        raise ValueError("invalid tenant id for filesystem namespace")
    return (get_default_keprix_root() / "tenants" / value).resolve()


def soul_path() -> Path:
    """Return the tenant SOUL path, or the shared base SOUL as fallback."""
    active = _active_tenant_id()
    if active:
        tenant_path = tenant_home(active) / "SOUL.md"
        if tenant_path.is_file():
            return tenant_path
    return get_default_keprix_root() / "SOUL.md"


def _active_tenant_id() -> str | None:
    if not tenant_home_isolation_enabled():
        return None
    try:
        from keprix.security.product_context import get_product_context_or_none

        context = get_product_context_or_none()
        return context.tenant_id if context else None
    except (ImportError, RuntimeError):
        return None


def shared_soul_write_error(path: str | Path) -> str | None:
    """Reject normal tenant writes to the shared identity file."""
    if not _active_tenant_id():
        return None
    try:
        target = Path(path).expanduser().resolve()
    except OSError:
        return None
    shared = (get_default_keprix_root() / "SOUL.md").resolve()
    if target != shared:
        return None
    try:
        from keprix.security.product_context import get_product_context_or_none

        context = get_product_context_or_none()
        if context and (context.has_scope("admin:soul") or context.has_scope("admin")):
            return None
    except (ImportError, RuntimeError):
        pass
    return (
        "Shared SOUL.md is read-only for normal tenant contexts; "
        "edit the tenant SOUL.md instead."
    )


@contextmanager
def tenant_home_scope(tenant_id: str) -> Iterator[Path]:
    """Temporarily bind all get_keprix_home callers to one tenant home."""
    home = tenant_home(tenant_id)
    home.mkdir(parents=True, exist_ok=True)
    token = set_keprix_home_override(home)
    try:
        yield home
    finally:
        reset_keprix_home_override(token)
