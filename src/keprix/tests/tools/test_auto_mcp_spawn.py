"""Tests for autonomous MCP spawn (prompt 161)."""

from unittest.mock import patch

import pytest


class TestSpawnMcp:
    def test_spawn_no_credentials_returns_message(self, monkeypatch, _isolate_keprix_home):
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        from tools.auto_mcp_spawn import spawn_mcp

        result = spawn_mcp(catalog_name="brave-search")
        assert "BRAVE_API_KEY" in result
        assert "/admin/mcp" in result

    def test_spawn_filesystem_no_credentials_needed(self, monkeypatch, _isolate_keprix_home):
        from tools.auto_mcp_spawn import spawn_mcp

        with patch("keprix_cli.mcp_config._save_mcp_server", return_value=True) as save_mock, patch(
            "tools.mcp_tool.register_server_runtime"
        ) as register_mock:
            result = spawn_mcp(catalog_name="filesystem")

        assert "active in this session" in result
        save_mock.assert_called_once()
        register_mock.assert_called_once()
        saved_name, saved_cfg = save_mock.call_args[0]
        assert saved_name == "filesystem"
        assert saved_cfg.get("auto_spawned") is True

    def test_spawn_duplicate_returns_message(self, monkeypatch, _isolate_keprix_home):
        from keprix_cli.mcp_config import _save_mcp_server
        from tools.auto_mcp_spawn import spawn_mcp

        _save_mcp_server(
            "filesystem",
            {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem"]},
        )
        result = spawn_mcp(catalog_name="filesystem")
        assert "already configured" in result

    def test_spawn_by_capability_matches_tags(self):
        from keprix_cli.autonomous_mcp_catalog import find_by_tags

        matches = find_by_tags(["web", "search"])
        assert any(e["key"] == "brave-search" for e in matches)

    def test_spawn_unknown_catalog_name(self):
        from tools.auto_mcp_spawn import spawn_mcp

        result = spawn_mcp(catalog_name="does-not-exist")
        assert "Unknown catalog entry" in result


class TestSpawnToolRegistration:
    def test_tool_not_available_when_flag_off(self, monkeypatch):
        monkeypatch.setenv("KEPRIX_AUTO_MCP_SPAWN", "false")
        from tools.registry import invalidate_check_fn_cache, registry

        invalidate_check_fn_cache()
        from tools.auto_mcp_spawn import check_auto_mcp_spawn_enabled

        assert check_auto_mcp_spawn_enabled() is False
        defs = registry.get_definitions({"keprix_spawn_mcp"})
        assert len(defs) == 0

    def test_tool_available_when_flag_on(self, monkeypatch):
        monkeypatch.setenv("KEPRIX_AUTO_MCP_SPAWN", "true")
        from tools.registry import invalidate_check_fn_cache, registry

        invalidate_check_fn_cache()
        from tools.auto_mcp_spawn import check_auto_mcp_spawn_enabled

        assert check_auto_mcp_spawn_enabled() is True
        defs = registry.get_definitions({"keprix_spawn_mcp"})
        assert len(defs) == 1


class TestAutoSpawnApi:
    @pytest.fixture(autouse=True)
    def _setup(self, _isolate_keprix_home, monkeypatch):
        from starlette.testclient import TestClient

        import keprix_state
        from keprix_constants import get_keprix_home
        from keprix_cli.web_server import _SESSION_HEADER_NAME, _SESSION_TOKEN, app

        self.client = TestClient(app)
        self.client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
        keprix_state.DEFAULT_DB_PATH = get_keprix_home() / "state.db"
        monkeypatch.setenv("KEPRIX_AUTO_MCP_SPAWN", "true")

    def test_auto_spawn_status_endpoint(self):
        r = self.client.get("/api/mcp/auto-spawn/status")
        assert r.status_code == 200
        body = r.json()
        assert body["enabled"] is True
        assert isinstance(body["auto_spawned_servers"], list)
        assert body["env_locked"] is True
        assert body["source"] == "env"

    def test_auto_spawn_settings_via_config(self, monkeypatch):
        monkeypatch.delenv("KEPRIX_AUTO_MCP_SPAWN", raising=False)
        r = self.client.put("/api/mcp/auto-spawn/settings", json={"enabled": True})
        assert r.status_code == 200
        body = r.json()
        assert body["enabled"] is True
        assert body["env_locked"] is False
        assert body["source"] == "config"

        from keprix_cli.mcp_spawn_settings import is_auto_mcp_spawn_enabled

        assert is_auto_mcp_spawn_enabled() is True

    def test_auto_spawn_settings_rejected_when_env_locked(self, monkeypatch):
        monkeypatch.setenv("KEPRIX_AUTO_MCP_SPAWN", "false")
        r = self.client.put("/api/mcp/auto-spawn/settings", json={"enabled": True})
        assert r.status_code == 400

    def test_spawn_tool_available_from_config(self, monkeypatch, _isolate_keprix_home):
        monkeypatch.delenv("KEPRIX_AUTO_MCP_SPAWN", raising=False)
        from keprix_cli.mcp_spawn_settings import set_auto_mcp_spawn_enabled
        from tools.registry import invalidate_check_fn_cache, registry

        set_auto_mcp_spawn_enabled(True)
        invalidate_check_fn_cache()
        from tools.auto_mcp_spawn import check_auto_mcp_spawn_enabled

        assert check_auto_mcp_spawn_enabled() is True
        defs = registry.get_definitions({"keprix_spawn_mcp"})
        assert len(defs) == 1

    def test_delete_auto_spawned_server(self, monkeypatch):
        from keprix_cli.mcp_config import _save_mcp_server

        _save_mcp_server(
            "filesystem",
            {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                "auto_spawned": True,
            },
        )
        with patch("tools.mcp_tool.unregister_server_runtime") as unregister_mock:
            r = self.client.delete("/api/mcp/auto-spawn/filesystem")
        assert r.status_code == 200
        unregister_mock.assert_called_once_with("filesystem")

        from keprix_cli.mcp_config import _get_mcp_servers

        assert "filesystem" not in _get_mcp_servers()

    def test_delete_manual_server_rejected(self):
        from keprix_cli.mcp_config import _save_mcp_server

        _save_mcp_server("manual", {"command": "npx", "args": ["-y", "pkg"]})
        r = self.client.delete("/api/mcp/auto-spawn/manual")
        assert r.status_code == 400
