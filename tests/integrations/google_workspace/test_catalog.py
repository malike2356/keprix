"""Google Workspace connector catalog tests."""

from __future__ import annotations

from keprix.integrations.connector_catalog import get_connector


def test_google_workspace_connector_catalog_entry() -> None:
    entry = get_connector("google-workspace")

    assert entry is not None
    assert entry.auth_pattern == "oauth"
    assert entry.docs_url == "/docs/integrations/google-workspace"
    assert "gws_calendar_list" in entry.sample_playbook_node["data"]["tools"]
