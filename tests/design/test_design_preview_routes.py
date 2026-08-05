"""Prompt 270 design preview API tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_design_preview_routes_open_select_and_message(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "style.css").write_text("button{color:red}", encoding="utf-8")
    (workspace / "index.html").write_text(
        '<html><head><link rel="stylesheet" href="style.css"></head><body><button class="primary">Save</button></body></html>',
        encoding="utf-8",
    )
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_WORKSPACE_ROOT", str(workspace))
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    opened = client.post("/api/design/preview/open", json={"path": str(workspace)})
    assert opened.status_code == 200
    session = opened.json()["session"]
    preview_url = opened.json()["preview_url"]
    assert preview_url.endswith("/render")

    rendered = client.get(preview_url)
    assert rendered.status_code == 200
    assert "keprix-design-selection" in rendered.text
    assert f"/api/design/preview/{session['session_id']}/asset/" in rendered.text

    asset = client.get(f"/api/design/preview/{session['session_id']}/asset/style.css")
    assert asset.status_code == 200
    assert "color:red" in asset.text

    selected = client.post(
        f"/api/design/preview/{session['session_id']}/selection",
        json={
            "selector": "button.primary",
            "html_snippet": '<button class="primary">Save</button>',
            "meta": {"tag": "button", "classes": ["primary"]},
        },
    )
    assert selected.status_code == 200
    assert selected.json()["session"]["selected_selector"] == "button.primary"

    message = client.get(f"/api/design/preview/{session['session_id']}/skill-message")
    assert message.status_code == 200
    assert "button.primary" in message.json()["message"]


def test_design_preview_route_rejects_traversal(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.html"
    outside.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_WORKSPACE_ROOT", str(workspace))
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    response = client.post("/api/design/preview/open", json={"path": str(outside)})

    assert response.status_code == 403
