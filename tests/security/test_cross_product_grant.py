"""Tests for security/cross_product_grant.py."""

from __future__ import annotations

import time

import pytest

from keprix.security.cross_product_grant import CrossProductGrant, CrossProductGrantStore


def _grant(
    grant_id="g1",
    grantor="aiva",
    grantee="abbis",
    resource_kind="document",
    resource_id="doc-1",
    workspace_id="ws-1",
    scopes=None,
    expires_at=None,
):
    return CrossProductGrant(
        grant_id=grant_id,
        grantor_product_id=grantor,
        grantee_product_id=grantee,
        resource_kind=resource_kind,
        resource_id=resource_id,
        workspace_id=workspace_id,
        granted_by="user-1",
        scopes=scopes or ["read"],
        expires_at=expires_at,
    )


@pytest.fixture
def store():
    return CrossProductGrantStore()


@pytest.mark.asyncio
async def test_allow_valid_grant(store):
    await store.add(_grant())
    ok = await store.is_allowed("abbis", "document", "doc-1", "ws-1", "read")
    assert ok


@pytest.mark.asyncio
async def test_deny_wrong_grantee(store):
    await store.add(_grant(grantee="abbis"))
    ok = await store.is_allowed("petraclus", "document", "doc-1", "ws-1", "read")
    assert not ok


@pytest.mark.asyncio
async def test_deny_wrong_resource(store):
    await store.add(_grant(resource_id="doc-1"))
    ok = await store.is_allowed("abbis", "document", "doc-999", "ws-1", "read")
    assert not ok


@pytest.mark.asyncio
async def test_deny_wrong_workspace(store):
    await store.add(_grant(workspace_id="ws-1"))
    ok = await store.is_allowed("abbis", "document", "doc-1", "ws-2", "read")
    assert not ok


@pytest.mark.asyncio
async def test_deny_write_scope_without_grant(store):
    await store.add(_grant(scopes=["read"]))
    ok = await store.is_allowed("abbis", "document", "doc-1", "ws-1", "write")
    assert not ok


@pytest.mark.asyncio
async def test_expired_grant_denied(store):
    await store.add(_grant(expires_at=time.time() - 1))
    ok = await store.is_allowed("abbis", "document", "doc-1", "ws-1", "read")
    assert not ok


@pytest.mark.asyncio
async def test_revoke_removes_grant(store):
    await store.add(_grant())
    await store.revoke("g1")
    ok = await store.is_allowed("abbis", "document", "doc-1", "ws-1", "read")
    assert not ok


@pytest.mark.asyncio
async def test_grants_for_returns_active_grants(store):
    await store.add(_grant(grant_id="g1"))
    await store.add(_grant(grant_id="g2", grantee="petraclus"))
    grants = await store.grants_for("abbis")
    assert len(grants) == 1
    assert grants[0].grant_id == "g1"


@pytest.mark.asyncio
async def test_purge_expired(store):
    await store.add(_grant(grant_id="old", expires_at=time.time() - 1))
    await store.add(_grant(grant_id="active"))
    removed = await store.purge_expired()
    assert removed == 1


def test_is_expired_false_for_none():
    grant = _grant(expires_at=None)
    assert not grant.is_expired


def test_is_expired_true_for_past():
    grant = _grant(expires_at=time.time() - 1)
    assert grant.is_expired


def test_to_dict():
    grant = _grant()
    d = grant.to_dict()
    assert d["grantor"] == "aiva"
    assert d["grantee"] == "abbis"
    assert "document/doc-1" in d["resource"]
