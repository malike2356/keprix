"""Consolidated smoke tests for Notion/Trello productivity pack (prompts 172-176)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUNDLED_SKILLS = PROJECT_ROOT / "src" / "keprix" / "skills"


class TestMcpCatalog172:
    def test_autonomous_catalog_entries(self):
        from keprix_cli.autonomous_mcp_catalog import get_entry

        notion = get_entry("notion")
        assert notion["auth_type"] == "oauth"
        assert notion["auto_spawnable"] is False

        notion_token = get_entry("notion-token")
        assert "NOTION_TOKEN" in notion_token["required_env"]

        trello = get_entry("trello")
        assert trello["required_env"] == ["TRELLO_API_KEY", "TRELLO_TOKEN"]

    def test_optional_mcp_manifests_exist(self):
        root = PROJECT_ROOT / "src" / "keprix" / "optional-mcps"
        assert (root / "notion" / "manifest.yaml").is_file()
        assert (root / "trello" / "manifest.yaml").is_file()


class TestMcpConnectionStatus173:
    def test_connection_fields_reports_needs_oauth(self, monkeypatch):
        from keprix_cli.mcp_connection_status import connection_fields

        monkeypatch.setattr(
            "keprix_cli.mcp_config._oauth_tokens_present",
            lambda name: False,
        )
        fields = connection_fields(
            "notion",
            {"url": "https://mcp.notion.com/mcp", "auth": "oauth", "enabled": True},
        )
        assert fields["connection_status"] == "needs_oauth"
        assert fields["oauth_connected"] is False


class TestNotionRagConnector174:
    def test_registry_lists_notion_connector(self):
        from keprix.rag_pipeline.connectors.registry import get_connector, list_connectors

        connectors = list_connectors()
        notion = next(item for item in connectors if item["id"] == "notion")
        assert "Notion" in notion["description"]

        connector = get_connector("notion", token="test-token", page_ids=["page-1"])
        assert connector.connector_id == "notion"


class TestProductivitySkills175:
    def test_bundled_skills_discovered(self):
        from keprix_constants import get_bundled_skills_dir
        from tools.skills_sync import _discover_bundled_skills

        bundled_dir = get_bundled_skills_dir(BUNDLED_SKILLS)
        names = {name for name, _ in _discover_bundled_skills(bundled_dir)}
        assert "trello" in names
        assert "productivity-integrations" in names

    def test_find_all_skills_includes_productivity(self, monkeypatch):
        import agent.skill_utils as skill_utils_mod
        import tools.skills_tool as skills_tool_mod

        monkeypatch.setattr(skills_tool_mod, "SKILLS_DIR", BUNDLED_SKILLS)
        monkeypatch.setattr(skill_utils_mod, "get_external_skills_dirs", lambda: [])
        monkeypatch.setattr(skills_tool_mod, "_get_disabled_skill_names", lambda: set())

        from tools.skills_tool import _find_all_skills

        names = {skill["name"] for skill in _find_all_skills()}
        assert "trello" in names
        assert "productivity-integrations" in names


@pytest.mark.integration
class TestLiveProductivityApis:
    def test_trello_list_boards_live(self):
        api_key = os.environ.get("TRELLO_API_KEY", "").strip()
        token = os.environ.get("TRELLO_TOKEN", "").strip()
        if not api_key or not token:
            pytest.skip("TRELLO_API_KEY and TRELLO_TOKEN required for live test")

        import json
        import urllib.request

        url = (
            f"https://api.trello.com/1/members/me/boards"
            f"?fields=name&key={api_key}&token={token}"
        )
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert isinstance(payload, list)

    def test_notion_connector_live_with_page_id(self):
        notion_token = (
            os.environ.get("KEPRIX_NOTION_TOKEN")
            or os.environ.get("NOTION_TOKEN")
            or os.environ.get("NOTION_API_KEY")
            or ""
        ).strip()
        page_id = os.environ.get("NOTION_TEST_PAGE_ID", "").strip()
        if not notion_token or not page_id:
            pytest.skip("NOTION_TEST_PAGE_ID and a Notion token required for live test")

        from keprix.rag_pipeline.connectors.notion import NotionSourceConnector

        connector = NotionSourceConnector(notion_token, page_ids=[page_id])
        docs = connector.list_documents()
        assert docs
        assert docs[0]["id"] == page_id
