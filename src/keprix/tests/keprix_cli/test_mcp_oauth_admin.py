"""Tests for MCP OAuth connect and Vault-backed catalog add (prompt 173)."""

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


class TestMcpConnectionStatus:
    @pytest.fixture(autouse=True)
    def _setup(self, _isolate_keprix_home):
        self.client = _client()

    def test_oauth_server_reports_needs_oauth(self):
        from keprix_cli.mcp_config import _save_mcp_server

        _save_mcp_server(
            "notion",
            {"url": "https://mcp.notion.com/mcp", "auth": "oauth"},
        )
        r = self.client.get("/api/mcp/servers")
        assert r.status_code == 200
        server = r.json()["servers"][0]
        assert server["name"] == "notion"
        assert server["connection_status"] == "needs_oauth"
        assert server["oauth_connected"] is False

    def test_oauth_server_connected_when_tokens_present(self, monkeypatch):
        from keprix_cli.mcp_config import _save_mcp_server

        _save_mcp_server(
            "notion",
            {"url": "https://mcp.notion.com/mcp", "auth": "oauth"},
        )
        monkeypatch.setattr(
            "keprix_cli.mcp_config._oauth_tokens_present",
            lambda name: name == "notion",
        )
        r = self.client.get("/api/mcp/servers")
        server = r.json()["servers"][0]
        assert server["oauth_connected"] is True
        assert server["connection_status"] == "connected"

    def test_trello_needs_credentials_without_env(self):
        from keprix_cli.mcp_config import _save_mcp_server

        _save_mcp_server(
            "trello",
            {
                "command": "npx",
                "args": ["-y", "@delorenj/mcp-server-trello"],
            },
        )
        r = self.client.get("/api/mcp/servers")
        server = next(s for s in r.json()["servers"] if s["name"] == "trello")
        assert server["connection_status"] == "needs_credentials"


class TestMcpOAuthStart:
    @pytest.fixture(autouse=True)
    def _setup(self, _isolate_keprix_home):
        self.client = _client()

    def test_oauth_start_returns_authorization_url(self, monkeypatch):
        from keprix_cli.mcp_config import _save_mcp_server

        _save_mcp_server(
            "notion",
            {"url": "https://mcp.notion.com/mcp", "auth": "oauth"},
        )
        monkeypatch.setattr(
            "keprix_cli.mcp_config.begin_mcp_oauth_authorization",
            lambda name, cfg: {"authorization_url": "https://example.com/oauth"},
        )
        r = self.client.post("/api/mcp/servers/notion/oauth/start")
        assert r.status_code == 200
        assert r.json()["authorization_url"] == "https://example.com/oauth"

    def test_oauth_start_already_connected(self, monkeypatch):
        from keprix_cli.mcp_config import _save_mcp_server

        _save_mcp_server(
            "notion",
            {"url": "https://mcp.notion.com/mcp", "auth": "oauth"},
        )
        monkeypatch.setattr(
            "keprix_cli.mcp_config.begin_mcp_oauth_authorization",
            lambda name, cfg: {
                "ok": True,
                "message": "Already connected",
                "oauth_connected": True,
            },
        )
        r = self.client.post("/api/mcp/servers/notion/oauth/start")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_oauth_start_rejects_non_oauth_server(self):
        from keprix_cli.mcp_config import _save_mcp_server

        _save_mcp_server("fs", {"command": "npx", "args": ["-y", "pkg"]})
        r = self.client.post("/api/mcp/servers/fs/oauth/start")
        assert r.status_code == 400


class TestMcpVaultCatalogAdd:
    @pytest.fixture(autouse=True)
    def _setup(self, _isolate_keprix_home):
        self.client = _client()

    def test_catalog_add_with_vault_env(self, monkeypatch):
        async def _fake_resolve(vault_env, user):
            return {"TRELLO_TOKEN": "vault-token-secret"}

        monkeypatch.setattr(
            "keprix_cli.mcp_vault_resolve.resolve_vault_env",
            _fake_resolve,
        )
        r = self.client.post(
            "/api/mcp/catalog/trello/add",
            json={
                "env": {"TRELLO_API_KEY": "key123"},
                "vault_env": {"TRELLO_TOKEN": "vault-item-1"},
            },
        )
        assert r.status_code == 200
        from keprix_cli.mcp_config import _get_mcp_servers

        saved = _get_mcp_servers()["trello"]
        assert saved["env"]["TRELLO_API_KEY"] == "key123"
        assert saved["env"]["TRELLO_TOKEN"] == "vault-token-secret"

        listed = self.client.get("/api/mcp/servers").json()["servers"]
        trello = next(s for s in listed if s["name"] == "trello")
        assert trello["env"]["TRELLO_TOKEN"] != "vault-token-secret"
        assert "..." in trello["env"]["TRELLO_TOKEN"]

    def test_vault_secret_keys_endpoint(self, monkeypatch):
        async def _fake_list(user):
            return [{"id": "item-1", "label": "Trello token"}]

        monkeypatch.setattr(
            "keprix_cli.mcp_vault_resolve.list_vault_secret_keys",
            _fake_list,
        )
        r = self.client.get("/api/mcp/vault/secret-keys")
        assert r.status_code == 200
        assert r.json()["keys"][0]["id"] == "item-1"
