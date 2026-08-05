"""Tests for security/isolation_query_filter.py."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from keprix.security.isolation_query_filter import (
    ISOLATED_TABLES,
    IsolatedDataPlane,
    check_isolation,
)
from keprix.security.isolation_violation import IsolationViolation
from keprix.security.product_context import (
    ProductContext,
    clear_product_context,
    set_product_context,
)


def _set_ctx(product_id="aiva", workspace_id="ws-1"):
    return set_product_context(
        ProductContext(product_id=product_id, workspace_id=workspace_id)
    )


@pytest.fixture(autouse=True)
def clear_ctx():
    yield
    tok = set_product_context(None)
    clear_product_context(tok)


def test_isolated_tables_contains_memories():
    assert "memories" in ISOLATED_TABLES
    assert "sessions" in ISOLATED_TABLES
    assert "documents" in ISOLATED_TABLES


def test_execute_without_where_raises():
    mock_plane = MagicMock()
    plane = IsolatedDataPlane(mock_plane)
    tok = _set_ctx()
    try:
        with pytest.raises(IsolationViolation, match="without WHERE"):
            plane.execute("SELECT * FROM memories", [])
    finally:
        clear_product_context(tok)


def test_execute_with_where_passes():
    mock_plane = MagicMock()
    mock_plane.execute.return_value = []
    plane = IsolatedDataPlane(mock_plane)
    tok = _set_ctx()
    try:
        plane.execute("SELECT * FROM memories WHERE workspace_id = ?", ["ws-1"])
        mock_plane.execute.assert_called_once()
    finally:
        clear_product_context(tok)


def test_execute_without_context_passes():
    mock_plane = MagicMock()
    mock_plane.execute.return_value = []
    plane = IsolatedDataPlane(mock_plane)
    # No context set - should not raise
    tok = set_product_context(None)
    clear_product_context(tok)
    plane.execute("SELECT * FROM memories", [])  # no context = no enforcement
    mock_plane.execute.assert_called_once()


def test_execute_isolated_injects_workspace():
    mock_plane = MagicMock()
    mock_plane.execute.return_value = []
    plane = IsolatedDataPlane(mock_plane)
    tok = _set_ctx(workspace_id="ws-abc", product_id="aiva")
    try:
        plane.execute_isolated(
            "SELECT * FROM memories WHERE workspace_id = :workspace_id",
            {},
        )
        call_params = mock_plane.execute.call_args[0][1]
        assert call_params["workspace_id"] == "ws-abc"
        assert call_params["product_id"] == "aiva"
    finally:
        clear_product_context(tok)


def test_check_isolation_workspace_mismatch_raises():
    tok = _set_ctx(workspace_id="ws-good")
    try:
        with pytest.raises(IsolationViolation, match="Workspace mismatch"):
            check_isolation("memories", workspace_id="ws-bad", product_id="aiva")
    finally:
        clear_product_context(tok)


def test_check_isolation_product_mismatch_raises():
    tok = _set_ctx(product_id="aiva", workspace_id="ws-1")
    try:
        with pytest.raises(IsolationViolation, match="Product mismatch"):
            check_isolation("memories", workspace_id="ws-1", product_id="abbis")
    finally:
        clear_product_context(tok)


def test_check_isolation_base_product_passes():
    tok = _set_ctx(product_id="keprix", workspace_id="ws-1")
    try:
        check_isolation("memories", workspace_id="ws-1", product_id="aiva")  # base product: no enforcement
    finally:
        clear_product_context(tok)


def test_check_isolation_without_context_passes():
    tok = set_product_context(None)
    clear_product_context(tok)
    check_isolation("memories", workspace_id="ws-x", product_id="aiva")  # no context = no enforcement
