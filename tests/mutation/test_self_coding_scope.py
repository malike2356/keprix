"""Tests for self-coding mutation scope (Prompt 153)."""

from __future__ import annotations

from keprix.mutation.self_coding_scope import (
    MUTATION_ALLOWED_PATHS,
    get_allowed_repo_root_relative_paths,
    validate_diff_scope,
)


def test_allowed_path_passes_validation():
    diff = """--- a/src/keprix/tools/my_tool.py
+++ b/src/keprix/tools/my_tool.py
@@ -0,0 +1,2 @@
+from tools.registry import registry
+pass
"""
    ok, violations = validate_diff_scope(diff)
    assert ok is True
    assert violations == []


def test_forbidden_path_fails_validation():
    diff = """--- a/src/keprix/security/auth.py
+++ b/src/keprix/security/auth.py
@@ -0,0 +1,1 @@
+pass
"""
    ok, violations = validate_diff_scope(diff)
    assert ok is False
    assert "src/keprix/security/auth.py" in violations


def test_path_outside_allowlist_fails_validation():
    diff = """--- a/src/keprix/api/server.py
+++ b/src/keprix/api/server.py
@@ -0,0 +1,1 @@
+pass
"""
    ok, violations = validate_diff_scope(diff)
    assert ok is False
    assert violations


def test_diff_with_mixed_paths_fails():
    diff = """--- a/src/keprix/tools/good.py
+++ b/src/keprix/tools/good.py
@@ -0,0 +1,1 @@
+pass
--- a/src/keprix/vault/secret.py
+++ b/src/keprix/vault/secret.py
@@ -0,0 +1,1 @@
+pass
"""
    ok, violations = validate_diff_scope(diff)
    assert ok is False
    assert any("vault" in path for path in violations)


def test_get_allowed_paths_returns_list():
    paths = get_allowed_repo_root_relative_paths()
    assert paths == MUTATION_ALLOWED_PATHS
