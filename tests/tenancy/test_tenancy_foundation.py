"""Tests for multi-tenancy foundation and isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.security.product_context import ProductContext, clear_product_context, set_product_context
from keprix.tenancy.isolation import TenantIsolationError, assert_tenant_owns
from keprix.tenancy.resolve import resolve_tenant_id
from keprix.tenancy.store import TenantConflictError, reset_tenant_store_for_tests


@pytest.fixture()
def tenant_store(tmp_path: Path):
    return reset_tenant_store_for_tests(tmp_path / "tenants.json")


def test_unique_slug(tenant_store) -> None:
    tenant_store.create(slug="acme", display_name="Acme", owner_user_id="u1")
    with pytest.raises(TenantConflictError):
        tenant_store.create(slug="acme", display_name="Other", owner_user_id="u2")


def test_resolve_header_and_membership(tenant_store) -> None:
    t = tenant_store.create(slug="acme", display_name="Acme", owner_user_id="owner1")
    tenant_store.add_membership(t.id, "member1", role="member")
    assert resolve_tenant_id(header_ref="acme", user={"id": "member1"}) == t.id
    assert resolve_tenant_id(user={"id": "member1"}) == t.id


def test_assert_tenant_owns_fails_closed() -> None:
    token = set_product_context(
        ProductContext(product_id="keprix", workspace_id="t1", tenant_id="t1")
    )
    try:
        with pytest.raises(TenantIsolationError):
            assert_tenant_owns({"id": "x", "tenant_id": "t2"}, soft_legacy=False)
    finally:
        clear_product_context(token)


def test_vical_cross_tenant_booking(tmp_path: Path, tenant_store) -> None:
    from keprix.vical.store import IsolationError, VicalStore

    store = VicalStore(path=tmp_path / "vical.json")
    a = set_product_context(ProductContext(product_id="keprix", workspace_id="a", tenant_id="tenant-a"))
    try:
        et = store.create_event_type(user_id="host", slug="consult", name="Consult", tenant_id="tenant-a")
        from datetime import datetime, timedelta, timezone

        start = datetime.now(timezone.utc) + timedelta(days=1)
        end = start + timedelta(minutes=30)
        booking = store.create_booking(
            user_id="host",
            event_type_id=et.id,
            guest_name="G",
            guest_email="g@example.com",
            starts_at=start,
            ends_at=end,
            tenant_id="tenant-a",
        )
    finally:
        clear_product_context(a)

    b = set_product_context(ProductContext(product_id="keprix", workspace_id="b", tenant_id="tenant-b"))
    try:
        with pytest.raises(IsolationError):
            store.get_booking("host", booking.id)
    finally:
        clear_product_context(b)
