"""Tests for web chat codebase awareness."""

from __future__ import annotations

from pathlib import Path

from keprix.api import codebase_context


def test_build_codebase_system_prompt_includes_repo_map(tmp_path, monkeypatch):
    root = tmp_path / "keprix"
    (root / "src" / "keprix").mkdir(parents=True)
    (root / "docs" / "features").mkdir(parents=True)
    (root / "README.md").write_text("# Keprix test install\n", encoding="utf-8")
    (root / "docs" / "features" / "chat.md").write_text("# Chat\n", encoding="utf-8")
    (root / "docs" / "features" / "self-coding-agent.md").write_text("# Mutation\n", encoding="utf-8")
    (root / "src" / "keprix" / "AGENTS.md").write_text("# Agents guide\n", encoding="utf-8")
    (root / "src" / "keprix" / "sample.py").write_text("def hello():\n    return 1\n", encoding="utf-8")

    monkeypatch.setenv("KEPRIX_REPO_ROOT", str(root))
    monkeypatch.setenv("KEPRIX_CODEBASE_AWARENESS", "true")
    codebase_context.build_codebase_system_prompt.cache_clear()

    prompt = codebase_context.build_codebase_system_prompt()

    assert "Security rules" in prompt
    assert "Mutation engine" in prompt
    assert "Repository map" in prompt
    assert "sample.py" in prompt
    assert "Agents guide" in prompt
    assert "# Chat" in prompt


def test_build_codebase_system_prompt_includes_capabilities_without_repo(monkeypatch):
    monkeypatch.setenv("KEPRIX_CODEBASE_AWARENESS", "true")
    monkeypatch.setattr(codebase_context, "resolve_repo_root", lambda: None)
    codebase_context.build_codebase_system_prompt.cache_clear()

    prompt = codebase_context.build_codebase_system_prompt()

    assert "Mutation engine" in prompt
    assert "self-hosted MIT-licensed AI agent OS" in prompt


def test_build_codebase_system_prompt_redacts_secrets(tmp_path, monkeypatch):
    root = tmp_path / "keprix"
    (root / "src" / "keprix").mkdir(parents=True)
    (root / "README.md").write_text(
        "Example key DEEPSEEK_API_KEY=sk-0123456789012345678901234567890\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("KEPRIX_REPO_ROOT", str(root))
    monkeypatch.setenv("KEPRIX_CODEBASE_AWARENESS", "true")
    codebase_context.build_codebase_system_prompt.cache_clear()

    prompt = codebase_context.build_codebase_system_prompt()

    assert "sk-0123456789012345678901234567890" not in prompt
    assert "[REDACTED" in prompt


def test_codebase_awareness_can_be_disabled(monkeypatch):
    monkeypatch.setenv("KEPRIX_CODEBASE_AWARENESS", "off")
    codebase_context.build_codebase_system_prompt.cache_clear()
    assert codebase_context.build_codebase_system_prompt() == ""


def test_resolve_repo_root_from_env(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("x", encoding="utf-8")
    (root / "src" / "keprix").mkdir(parents=True)

    monkeypatch.setenv("KEPRIX_REPO_ROOT", str(root))
    assert codebase_context.resolve_repo_root() == Path(root).resolve()
