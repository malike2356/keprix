"""Tests for security/product_context.py."""

from __future__ import annotations

import pytest

from keprix.security.product_context import (
    ProductContext,
    clear_product_context,
    get_product_context,
    get_product_context_or_none,
    set_product_context,
)


def _ctx(**kwargs):
    defaults = {
        "product_id": "aiva",
        "workspace_id": "ws-123",
        "tenant_id": "tenant-1",
        "session_id": "sess-abc",
        "scopes": frozenset({"read:sessions", "write:sessions"}),
    }
    defaults.update(kwargs)
    return ProductContext(**defaults)


def test_no_context_raises():
    # Clear any lingering context from other tests
    tok = set_product_context(None)
    clear_product_context(tok)
    with pytest.raises(RuntimeError, match="No product context"):
        get_product_context()


def test_set_and_get_context():
    ctx = _ctx()
    token = set_product_context(ctx)
    try:
        retrieved = get_product_context()
        assert retrieved.product_id == "aiva"
        assert retrieved.workspace_id == "ws-123"
    finally:
        clear_product_context(token)


def test_get_or_none_without_context():
    tok = set_product_context(None)
    clear_product_context(tok)
    assert get_product_context_or_none() is None


def test_get_or_none_with_context():
    ctx = _ctx()
    token = set_product_context(ctx)
    try:
        assert get_product_context_or_none() is not None
    finally:
        clear_product_context(token)


def test_context_is_immutable():
    ctx = _ctx()
    with pytest.raises((AttributeError, TypeError)):
        ctx.product_id = "abbis"  # type: ignore


def test_is_base_product_true():
    ctx = _ctx(product_id="keprix")
    assert ctx.is_base_product()


def test_is_base_product_false():
    ctx = _ctx(product_id="aiva")
    assert not ctx.is_base_product()


def test_has_scope_true():
    ctx = _ctx(scopes=frozenset({"read:sessions"}))
    assert ctx.has_scope("read:sessions")


def test_has_scope_false():
    ctx = _ctx(scopes=frozenset())
    assert not ctx.has_scope("write:admin")


def test_to_dict():
    ctx = _ctx()
    d = ctx.to_dict()
    assert d["product_id"] == "aiva"
    assert "workspace_id" in d
    assert isinstance(d["scopes"], list)
