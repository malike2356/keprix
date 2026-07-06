"""Tests for the autonomous MCP catalog (npm well-known servers)."""

import pytest


def _client():
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")
    import keprix_state
    from keprix_constants import get_keprix_home
    from keprix_cli.web_server import app, _SESSION_HEADER_NAME, _SESSION_TOKEN

    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    keprix_state.DEFAULT_DB_PATH = get_keprix_home() / "state.db"
    return client


class TestAutonomousMcpCatalog:
    def test_catalog_has_seventeen_entries(self):
        from keprix_cli.autonomous_mcp_catalog import get_catalog

        catalog = get_catalog()
        assert len(catalog) == 17
        keys = {e["key"] for e in catalog}
        assert "filesystem" in keys
        assert "github" in keys
        assert "notion" in keys
        assert "notion-token" in keys
        assert "trello" in keys

    def test_notion_entry_oauth_http(self):
        from keprix_cli.autonomous_mcp_catalog import get_entry

        entry = get_entry("notion")
        assert entry["auth_type"] == "oauth"
        assert entry["url"] == "https://mcp.notion.com/mcp"
        assert entry["transport"] == "http"
        assert entry["auto_spawnable"] is False

    def test_trello_entry_credentials(self):
        from keprix_cli.autonomous_mcp_catalog import get_entry

        entry = get_entry("trello")
        assert entry["required_env"] == ["TRELLO_API_KEY", "TRELLO_TOKEN"]
        assert entry["command"] == "npx"

    def test_find_by_tags_includes_trello(self):
        from keprix_cli.autonomous_mcp_catalog import find_by_tags

        keys = {m["key"] for m in find_by_tags(["kanban"])}
        assert "trello" in keys

    def test_get_entry_raises_for_unknown(self):
        from keprix_cli.autonomous_mcp_catalog import get_entry

        with pytest.raises(KeyError):
            get_entry("not-a-real-mcp")

    def test_find_by_tags_matches_any(self):
        from keprix_cli.autonomous_mcp_catalog import find_by_tags

        matches = find_by_tags(["web", "search"])
        keys = {m["key"] for m in matches}
        assert "fetch" in keys or "brave-search" in keys


class TestAutonomousMcpCatalogApi:
    @pytest.fixture(autouse=True)
    def _setup(self, _isolate_keprix_home):
        self.client = _client()

    def test_catalog_endpoint_returns_suggested_list(self):
        r = self.client.get("/api/mcp/catalog")
        assert r.status_code == 200
        body = r.json()
        assert "catalog" in body
        assert len(body["catalog"]) == 17
        entry = body["catalog"][0]
        assert {"key", "label", "description", "transport", "required_env", "capability_tags", "auto_spawnable"} <= set(
            entry
        )

    def test_add_notion_oauth_from_catalog(self):
        r = self.client.post("/api/mcp/catalog/notion/add", json={})
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "notion"
        assert data["transport"] == "http"

        from keprix_cli.mcp_config import _get_mcp_servers

        saved = _get_mcp_servers()["notion"]
        assert saved["url"] == "https://mcp.notion.com/mcp"
        assert saved["auth"] == "oauth"
        assert "command" not in saved

    def test_add_trello_with_env(self):
        r = self.client.post(
            "/api/mcp/catalog/trello/add",
            json={
                "env": {
                    "TRELLO_API_KEY": "key123",
                    "TRELLO_TOKEN": "token456",
                }
            },
        )
        assert r.status_code == 200
        from keprix_cli.mcp_config import _get_mcp_servers

        saved = _get_mcp_servers()["trello"]
        assert saved["command"] == "npx"
        assert saved["args"] == ["-y", "@delorenj/mcp-server-trello"]
        assert saved["env"]["TRELLO_API_KEY"] == "key123"

    def test_add_notion_token_requires_env(self):
        r = self.client.post("/api/mcp/catalog/notion-token/add", json={})
        assert r.status_code == 400
        assert "NOTION_TOKEN" in r.json()["detail"]

    def test_add_notion_token_with_env(self):
        r = self.client.post(
            "/api/mcp/catalog/notion-token/add",
            json={"env": {"NOTION_TOKEN": "ntn_test"}},
        )
        assert r.status_code == 200
        from keprix_cli.mcp_config import _get_mcp_servers

        assert _get_mcp_servers()["notion-token"]["env"]["NOTION_TOKEN"] == "ntn_test"

    def test_add_filesystem_from_catalog(self):
        r = self.client.post("/api/mcp/catalog/filesystem/add", json={})
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "filesystem"
        assert data["transport"] == "stdio"

        from keprix_cli.mcp_config import _get_mcp_servers

        saved = _get_mcp_servers()["filesystem"]
        assert saved["command"] == "npx"
        assert saved["args"] == ["-y", "@modelcontextprotocol/server-filesystem"]
        assert saved.get("auto_spawned") is False

    def test_add_github_with_env(self):
        r = self.client.post(
            "/api/mcp/catalog/github/add",
            json={"env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"}},
        )
        assert r.status_code == 200
        from keprix_cli.mcp_config import _get_mcp_servers

        assert _get_mcp_servers()["github"]["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"] == "ghp_xxx"

    def test_add_duplicate_returns_409(self):
        self.client.post("/api/mcp/catalog/filesystem/add", json={})
        r = self.client.post("/api/mcp/catalog/filesystem/add", json={})
        assert r.status_code == 409

    def test_add_unknown_returns_404(self):
        r = self.client.post("/api/mcp/catalog/no-such-key/add", json={})
        assert r.status_code == 404
