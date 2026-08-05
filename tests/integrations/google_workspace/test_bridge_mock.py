"""Google Workspace bridge tests with mocked sidecar calls."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from keprix.integrations.google_workspace.bridge import GoogleWorkspaceBridge, GoogleWorkspaceConfig
from keprix.integrations.google_workspace.oauth_store import GoogleWorkspaceOAuthStore


def test_bridge_calendar_list_uses_json_sidecar(tmp_path: Path, monkeypatch) -> None:
    credentials = tmp_path / "client.json"
    credentials.write_text(json.dumps({"installed": {"client_id": "abc.apps.googleusercontent.com"}}), encoding="utf-8")
    config = GoogleWorkspaceConfig(
        enabled=True,
        credentials_path=str(credentials),
        token_path=str(tmp_path / "token.json"),
        bridge_command="/usr/local/bin/gws-bridge",
    )
    seen: dict[str, object] = {}

    def fake_run(command, input, text, capture_output, check, timeout):
        seen["command"] = command
        seen["payload"] = json.loads(input)
        return SimpleNamespace(returncode=0, stdout=json.dumps({"events": [{"summary": "Planning"}]}), stderr="")

    monkeypatch.setattr("keprix.integrations.google_workspace.bridge.subprocess.run", fake_run)

    result = GoogleWorkspaceBridge(config=config).calendar_list(max_results=3)

    assert result["events"][0]["summary"] == "Planning"
    assert seen["command"] == ["/usr/local/bin/gws-bridge"]
    assert seen["payload"] == {
        "tool": "gws_calendar_list",
        "args": {"time_min": None, "max_results": 3},
        "token_path": str(tmp_path / "token.json"),
        "credentials_path": str(credentials),
    }


def test_write_tools_require_confirmation(tmp_path: Path) -> None:
    bridge = GoogleWorkspaceBridge(
        config=GoogleWorkspaceConfig(token_path=str(tmp_path / "token.json")),
        store=GoogleWorkspaceOAuthStore(tmp_path / "token.json"),
    )

    gmail = bridge.gmail_send(to="a@example.com", subject="Hi", body="Body")
    event = bridge.calendar_create(summary="Call", start="2026-07-09T10:00:00Z", end="2026-07-09T10:30:00Z")

    assert gmail["requires_confirmation"] is True
    assert event["requires_confirmation"] is True


def test_status_reports_missing_credentials(tmp_path: Path) -> None:
    bridge = GoogleWorkspaceBridge(config=GoogleWorkspaceConfig(token_path=str(tmp_path / "token.json")))

    status = bridge.status()

    assert status["connected"] is False
    assert "GOOGLE_WORKSPACE_CREDENTIALS_PATH" in status["missing_setup"]
    assert "Google Workspace is not connected" in status["setup_error"]
