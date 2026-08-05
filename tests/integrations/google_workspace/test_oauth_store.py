"""Google Workspace OAuth token store tests."""

from __future__ import annotations

from pathlib import Path

from keprix.integrations.google_workspace.oauth_store import GoogleWorkspaceOAuthStore


def test_oauth_store_saves_public_status(tmp_path: Path) -> None:
    store = GoogleWorkspaceOAuthStore(tmp_path / "token.json")

    token = store.save_from_callback(
        {
            "code": "code-123",
            "account_email": "owner@example.com",
            "scopes": ["gmail.readonly", "calendar"],
        }
    )

    assert token.connected is True
    assert store.load().account_email == "owner@example.com"
    public = store.load().public_dict()
    assert public["connected"] is True
    assert "access_token" not in public


def test_oauth_store_treats_empty_file_as_disconnected(tmp_path: Path) -> None:
    token_path = tmp_path / "token.json"
    token_path.write_text("", encoding="utf-8")

    token = GoogleWorkspaceOAuthStore(token_path).load()

    assert token.connected is False
