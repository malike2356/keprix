"""Tests for coding context loader and export."""

from __future__ import annotations

from pathlib import Path

from keprix.coding.context_loader import load_context
from keprix.coding.repo_map import build_repo_map
from keprix.coding.voice_to_code import voice_to_coding_request
from keprix.coding.web_chat_export import export_web_chat_bundle


def test_voice_to_code_normalizes_transcript() -> None:
    result = voice_to_coding_request("hey keprix add a health check endpoint")
    assert "health check" in result.lower()
    assert "Implement the following" not in result


def test_voice_to_code_wraps_non_coding_phrase() -> None:
    result = voice_to_coding_request("the dashboard looks slow")
    assert result.startswith("Implement the following coding task:")


def test_context_loader_redacts_secrets(tmp_path: Path) -> None:
    repo = tmp_path
    secret_file = repo / "notes.txt"
    secret_file.write_text("api_key=sk-abcdefghijklmnopqrstuvwxyz1234567890\n", encoding="utf-8")
    context = load_context(
        repo_path=repo,
        files=["notes.txt"],
        urls=["https://example.com/docs"],
        issue_text="Fix notes formatting",
    )
    assert context.coding_request == "Fix notes formatting"
    assert len(context.artifacts) >= 2
    file_artifact = next(item for item in context.artifacts if item.kind == "file")
    assert "REDACTED" in file_artifact.redacted_preview or "sk-" not in file_artifact.redacted_preview


def test_web_chat_export_bundle(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")
    context = load_context(repo_path=repo, files=["main.py"], issue_text="Refactor main")
    bundle = export_web_chat_bundle(
        context=context,
        repo_map=build_repo_map(repo),
        patch="*** Begin Patch\n*** End Patch\n",
        test_summary="1 passed",
    )
    assert "Refactor main" in bundle.markdown
    assert "Repo map" in bundle.markdown
    assert bundle.json_summary["artifact_count"] >= 1
