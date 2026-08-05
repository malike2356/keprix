"""Prompt 270 design preview server tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from keprix.design.preview_server import (
    build_design_skill_message,
    inject_preview_bridge,
    resolve_preview_entry,
)
from keprix.design.preview_session_store import PreviewSession


def test_resolve_preview_entry_rejects_path_outside_workspace(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.html"
    outside.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setenv("KEPRIX_WORKSPACE_ROOT", str(workspace))

    with pytest.raises(HTTPException) as exc:
        resolve_preview_entry(str(outside), None)

    assert exc.value.status_code == 403


def test_resolve_preview_entry_accepts_workspace_html(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    entry = workspace / "index.html"
    entry.write_text("<html><body>Hi</body></html>", encoding="utf-8")
    monkeypatch.setenv("KEPRIX_WORKSPACE_ROOT", str(workspace))

    root, target = resolve_preview_entry(str(workspace), None)

    assert root == workspace.resolve()
    assert target == entry.resolve()


def test_inject_preview_bridge_adds_base_and_selection_script() -> None:
    html = "<html><head><title>x</title></head><body><button>Go</button></body></html>"

    rendered = inject_preview_bridge(html, session_id="dp-test")

    assert '<base href="/api/design/preview/dp-test/asset/">' in rendered
    assert "keprix-design-selection" in rendered
    assert "/api/design/preview/" in rendered


def test_design_skill_message_includes_selector_context() -> None:
    session = PreviewSession(
        session_id="dp-test",
        root_path="/workspace/app",
        artifact_id=None,
        entry_file="index.html",
        selected_selector="main > button.primary",
        selected_html_snippet='<button class="primary">Save</button>',
        selected_meta={"tag": "button"},
    )

    message = build_design_skill_message(session)

    assert "/skill claude-design" in message
    assert "/skill impeccable" in message
    assert "main > button.primary" in message
    assert "Save" in message
