"""Prompt 263 simplified mode tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.agent_os.simplified_mode import SimplifiedModeConfig, blocked_path, set_simplified_mode
from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user
from keprix.ui_contract.navigation import navigation_for_role


def test_simplified_mode_blocks_advanced_paths_and_filters_nav(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    set_simplified_mode(SimplifiedModeConfig(simplified_mode=True))

    assert blocked_path("/agent-studio")
    assert blocked_path("/playbooks/studio/brief")
    assert not blocked_path("/agent-os")
    nav = navigation_for_role("user")
    ids = {item["id"] for item in nav["items"]}
    assert "agent-studio" not in ids
    assert "agent-os-board" in ids


def test_simplified_mode_routes_admin_update_and_guard(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "admin", "role": "admin"}
    client = TestClient(app)

    saved = client.put("/api/agent-os/simplified-mode", json={"simplified_mode": True})
    assert saved.status_code == 200
    guard = client.get("/api/agent-os/simplified-mode/guard?path=/agent-studio")
    assert guard.status_code == 200
    assert guard.json() == {"blocked": True, "redirect": "/agent-os"}


def test_simplified_mode_update_requires_admin(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    response = client.put("/api/agent-os/simplified-mode", json={"simplified_mode": True})
    assert response.status_code == 403
