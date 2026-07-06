"""Agent server registry tests (Prompt 61)."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.control_center.agent_server_registry import list_servers, register_server
from keprix.control_center.store import ControlCenterStore, reset_control_center_store
from keprix.security.vault_service import reset_vault_service


@pytest.fixture
def store(tmp_path: Path, monkeypatch):
    reset_vault_service()
    reset_control_center_store(ControlCenterStore(base_dir=tmp_path / "control_center"))
    monkeypatch.setattr(
        "keprix.control_center.path_policy.allowed_workspace_roots",
        lambda: [tmp_path.resolve()],
    )
    yield
    reset_control_center_store(None)
    reset_vault_service()


@pytest.mark.asyncio
async def test_register_local_agent_server(store, tmp_path: Path):
    server = await register_server(
        name="local-agent",
        url="http://127.0.0.1:8000",
        owner="admin",
        workspace_root=str(tmp_path),
        token="secret-token-value",
        capabilities=["coding", "playbook"],
    )
    assert server["name"] == "local-agent"
    assert server["has_token"] is True
    assert server["health_status"] == "unknown"
    listed = list_servers()
    assert len(listed) == 1
    assert listed[0]["workspace_root"] == str(tmp_path.resolve())


@pytest.mark.asyncio
async def test_register_rejects_non_allowlisted_workspace(store, tmp_path: Path):
    with pytest.raises(Exception):
        await register_server(
            name="bad-root",
            url="http://127.0.0.1:8000",
            owner="admin",
            workspace_root=str(tmp_path / ".." / "outside"),
        )
