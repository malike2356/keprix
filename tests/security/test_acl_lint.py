"""Tests for keprix_cli/acl_lint.py."""

from __future__ import annotations

import pytest

from keprix.security.tool_acl import ToolACL
from keprix_cli.acl_lint import lint_product, run_lint, LintResult


KNOWN_TOOLS = [
    "crm:list", "crm:create", "crm:delete",
    "terminal:run", "terminal:ssh",
    "search:web", "email:send",
]


@pytest.fixture
def acl():
    a = ToolACL()
    a.load_product("aiva", allowed_tools=["crm:*"], denied_tools=[])
    a.load_product("abbis", allowed_tools=["search:web"], denied_tools=[])
    return a


def test_clean_config_no_issues(acl):
    result = lint_product("aiva", acl, KNOWN_TOOLS)
    assert not result.has_errors
    assert not result.has_warnings


def test_empty_allowed_list_warns(acl):
    acl.load_product("petraclus", allowed_tools=[], denied_tools=[])
    result = lint_product("petraclus", acl, KNOWN_TOOLS)
    assert result.has_warnings
    messages = [i.message for i in result.issues]
    assert any("empty" in m for m in messages)


def test_unknown_tool_in_allowed_warns(acl):
    acl.load_product("aiva", allowed_tools=["crm:nonexistent"], denied_tools=[])
    result = lint_product("aiva", acl, KNOWN_TOOLS)
    assert result.has_warnings
    assert any("not installed" in i.message for i in result.issues)


def test_unknown_tool_in_allowed_is_error_when_strict(acl):
    acl.load_product("aiva", allowed_tools=["crm:nonexistent"], denied_tools=[])
    result = lint_product("aiva", acl, KNOWN_TOOLS, strict=True)
    assert result.has_errors


def test_wildcard_patterns_skip_unknown_check(acl):
    acl.load_product("aiva", allowed_tools=["crm:*"], denied_tools=["terminal:*"])
    result = lint_product("aiva", acl, KNOWN_TOOLS)
    assert not result.has_errors
    assert not result.has_warnings


def test_conflict_exact_pattern_in_both_is_error(acl):
    acl.load_product("aiva", allowed_tools=["crm:list"], denied_tools=["crm:list"])
    result = lint_product("aiva", acl, KNOWN_TOOLS)
    assert result.has_errors
    assert any("both allowed_tools and denied_tools" in i.message for i in result.issues)


def test_star_in_both_warns_about_shadow(acl):
    acl.load_product("aiva", allowed_tools=["*"], denied_tools=["*"])
    result = lint_product("aiva", acl, KNOWN_TOOLS)
    messages = [i.message for i in result.issues]
    assert any("shadows" in m for m in messages)


def test_unregistered_product_is_error(acl):
    result = lint_product("phantom", acl, KNOWN_TOOLS)
    assert result.has_errors
    assert any("not registered" in i.message for i in result.issues)


def test_base_product_unregistered_no_error(acl):
    # keprix is the base product; it's allowed to not be explicitly registered
    result = lint_product("keprix", acl, KNOWN_TOOLS)
    assert not result.has_errors


def test_run_lint_multiple_products(acl):
    results = run_lint(["aiva", "abbis"], acl=acl, known_tools=KNOWN_TOOLS)
    assert len(results) == 2
    assert all(isinstance(r, LintResult) for r in results)
