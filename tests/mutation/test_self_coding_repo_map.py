"""Repo map scoping for self-coding mutation."""

from __future__ import annotations

from pathlib import Path

from keprix.coding.repo_map import build_repo_map
from keprix.mutation.self_coding_scope import get_allowed_repo_root_relative_paths


def test_scoped_repo_map_excludes_security(tmp_path):
    repo = tmp_path / "repo"
    tools = repo / "src/keprix/tools"
    security = repo / "src/keprix/security"
    tools.mkdir(parents=True)
    security.mkdir(parents=True)
    (tools / "allowed.py").write_text("x = 1\n", encoding="utf-8")
    (security / "secret.py").write_text("SECRET = 1\n", encoding="utf-8")

    scoped = build_repo_map(repo, allowed_paths=get_allowed_repo_root_relative_paths())
    assert "src/keprix/tools/allowed.py" in scoped.files
    assert "src/keprix/security/secret.py" not in scoped.files
