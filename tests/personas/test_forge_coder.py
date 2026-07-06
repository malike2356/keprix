"""Tests for FORGE coder module."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.coding.patcher import PatchBundle
from keprix.coding.scoped_replace import EditOperation, EditResult
from keprix.personas.forge.coder import FORGE_SANDBOX_MODE, ForgeCoder


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def hello() -> str:\n    return 'hi'\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def coder(repo_root: Path) -> ForgeCoder:
    return ForgeCoder(repo_root=repo_root)


def test_review_catches_secret(coder: ForgeCoder) -> None:
    source = 'API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"'
    result = coder.review_code(source, file_path="config.py")
    assert not result.passed
    assert any(finding.rule == "no_secrets" for finding in result.findings)


def test_review_passes_clean_python(coder: ForgeCoder) -> None:
    source = "def add(a: int, b: int) -> int:\n    return a + b\n\ndef test_add() -> None:\n    assert add(1, 2) == 3\n"
    result = coder.review_code(source, file_path="math.py")
    assert result.passed


def test_review_flags_missing_type_hints(coder: ForgeCoder) -> None:
    source = "def add(a, b):\n    return a + b\n"
    result = coder.review_code(source, file_path="math.py")
    assert not result.passed
    assert any(finding.rule == "type_hints" for finding in result.findings)


def test_sandbox_blocks_host_path(coder: ForgeCoder) -> None:
    decision = coder.enforce_sandbox("/etc/passwd")
    assert not decision.allowed
    assert decision.needs_approval


def test_sandbox_allows_repo_path(coder: ForgeCoder) -> None:
    decision = coder.enforce_sandbox("src/app.py")
    assert decision.allowed


def test_prepare_patch_requires_approval_for_bad_code(coder: ForgeCoder) -> None:
    content = 'TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"'
    edit = EditResult(
        ok=True,
        path="src/bad.py",
        operation=EditOperation.CREATE,
        old_content_hash="",
        new_content_hash="abc",
        diff_preview="",
        rollback_data={"new_content": content},
    )
    bundle = PatchBundle(patch_text="", edits=[edit])
    prep = coder.prepare_patch(bundle)
    assert prep["needs_approval"]
    assert not prep["passed_review"]


def test_apply_patch_blocked_without_approval(coder: ForgeCoder) -> None:
    edit = EditResult(
        ok=True,
        path="src/new.py",
        operation=EditOperation.CREATE,
        old_content_hash="",
        new_content_hash="abc",
        diff_preview="",
        rollback_data={"new_content": "def run() -> None:\n    pass\n"},
    )
    bundle = PatchBundle(patch_text="", edits=[edit])
    result = coder.apply_patch_with_approval(bundle, approved=False)
    assert not result["applied"]


def test_generate_code_runs_in_sandbox(coder: ForgeCoder) -> None:
    result = coder.generate_code("compute mean of sample data")
    assert result.session_id
    assert result.code


def test_sandbox_mode_is_non_main() -> None:
    assert FORGE_SANDBOX_MODE == "non-main"
