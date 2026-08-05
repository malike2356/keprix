"""Tests for security/tool_acl.py."""

from __future__ import annotations

import pytest

from keprix.security.tool_acl import ACLDecision, ToolACL
from keprix.security.tool_acl_denied import ToolACLDenied


@pytest.fixture
def acl():
    return ToolACL()


def test_base_product_is_curated_by_default(acl):
    assert acl.check("keprix", "search:web") == ACLDecision.ALLOWED
    assert acl.check("keprix", "terminal:run") == ACLDecision.DENIED


def test_base_product_respects_denied_list(acl):
    acl.load_product("keprix", allowed_tools=["*"], denied_tools=["terminal:run"])
    assert acl.check("keprix", "terminal:run") == ACLDecision.DENIED


def test_unknown_product_returns_unknown(acl):
    decision = acl.check("phantom", "crm:list")
    assert decision == ACLDecision.UNKNOWN_PRODUCT


def test_exact_match_allowed(acl):
    acl.load_product("aiva", allowed_tools=["crm:create_contact"])
    assert acl.check("aiva", "crm:create_contact") == ACLDecision.ALLOWED


def test_exact_match_not_in_list(acl):
    acl.load_product("aiva", allowed_tools=["crm:create_contact"])
    assert acl.check("aiva", "crm:delete_contact") == ACLDecision.DENIED_NOT_LISTED


def test_category_wildcard_matches_namespace(acl):
    acl.load_product("aiva", allowed_tools=["crm:*"])
    assert acl.check("aiva", "crm:create_contact") == ACLDecision.ALLOWED
    assert acl.check("aiva", "crm:delete_contact") == ACLDecision.ALLOWED


def test_category_wildcard_does_not_match_other_namespace(acl):
    acl.load_product("aiva", allowed_tools=["crm:*"])
    assert acl.check("aiva", "terminal:run") == ACLDecision.DENIED_NOT_LISTED


def test_star_wildcard_allows_all(acl):
    acl.load_product("aiva", allowed_tools=["*"])
    assert acl.check("aiva", "terminal:run") == ACLDecision.ALLOWED
    assert acl.check("aiva", "email:send") == ACLDecision.ALLOWED


def test_denied_list_overrides_allowed(acl):
    acl.load_product("aiva", allowed_tools=["*"], denied_tools=["terminal:run"])
    assert acl.check("aiva", "terminal:run") == ACLDecision.DENIED


def test_denied_category_wildcard_overrides_allowed(acl):
    acl.load_product("aiva", allowed_tools=["*"], denied_tools=["terminal:*"])
    assert acl.check("aiva", "terminal:run") == ACLDecision.DENIED
    assert acl.check("aiva", "terminal:ssh") == ACLDecision.DENIED
    assert acl.check("aiva", "crm:list") == ACLDecision.ALLOWED


def test_empty_allowlist_denies_all(acl):
    acl.load_product("abbis", allowed_tools=[], denied_tools=[])
    assert acl.check("abbis", "crm:list") == ACLDecision.DENIED_NOT_LISTED


def test_check_or_raise_passes_for_allowed(acl):
    acl.load_product("aiva", allowed_tools=["crm:*"])
    acl.check_or_raise("aiva", "crm:list")  # should not raise


def test_check_or_raise_raises_for_denied(acl):
    acl.load_product("aiva", allowed_tools=["crm:*"], denied_tools=["crm:delete_contact"])
    with pytest.raises(ToolACLDenied) as exc_info:
        acl.check_or_raise("aiva", "crm:delete_contact")
    assert exc_info.value.product_id == "aiva"
    assert exc_info.value.tool_name == "crm:delete_contact"


def test_check_or_raise_raises_for_not_listed(acl):
    acl.load_product("aiva", allowed_tools=["crm:*"])
    with pytest.raises(ToolACLDenied) as exc_info:
        acl.check_or_raise("aiva", "terminal:run")
    assert "not in the allowlist" in exc_info.value.reason


def test_check_or_raise_raises_for_unknown_product(acl):
    with pytest.raises(ToolACLDenied) as exc_info:
        acl.check_or_raise("phantom", "crm:list")
    assert "not registered" in exc_info.value.reason


def test_resolved_tools_returns_all_decisions(acl):
    acl.load_product("aiva", allowed_tools=["crm:*"], denied_tools=["crm:delete_contact"])
    catalog = ["crm:list", "crm:create", "crm:delete_contact", "terminal:run"]
    result = acl.resolved_tools("aiva", catalog)
    assert result["crm:list"] == ACLDecision.ALLOWED
    assert result["crm:create"] == ACLDecision.ALLOWED
    assert result["crm:delete_contact"] == ACLDecision.DENIED
    assert result["terminal:run"] == ACLDecision.DENIED_NOT_LISTED


def test_snapshot_returns_all_products(acl):
    acl.load_product("aiva", allowed_tools=["crm:*"])
    acl.load_product("abbis", allowed_tools=["search:*"])
    snap = acl.snapshot()
    assert "aiva" in snap
    assert "abbis" in snap
    assert snap["aiva"]["allowed_tools"] == ["crm:*"]


def test_load_product_overwrites_previous(acl):
    acl.load_product("aiva", allowed_tools=["crm:*"])
    acl.load_product("aiva", allowed_tools=["email:*"])
    snap = acl.snapshot()
    assert snap["aiva"]["allowed_tools"] == ["email:*"]


def test_list_registered_products(acl):
    acl.load_product("aiva", allowed_tools=["*"])
    acl.load_product("abbis", allowed_tools=["search:*"])
    products = acl.list_registered_products()
    assert "aiva" in products
    assert "abbis" in products


def test_tool_acl_denied_to_tool_result():
    exc = ToolACLDenied(product_id="aiva", tool_name="terminal:run", reason="explicitly denied")
    result = exc.to_tool_result(tool_call_id="call-123")
    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call-123"
    assert result["_keprix_acl_denied"] is True
    assert "terminal:run" in result["content"]
    assert "aiva" in result["content"]
