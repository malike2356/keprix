"""Semantic rename request and service contract tests."""

from types import SimpleNamespace

import pytest

from agent.lsp.client import LSPClient, LSPProtocolError


@pytest.mark.asyncio
async def test_rename_rejects_server_without_rename_capability() -> None:
    client = LSPClient(
        server_id="fake",
        workspace_root="/tmp",
        command=["unused"],
    )
    client._state = "running"
    client._proc = SimpleNamespace(
        returncode=None,
        stdin=SimpleNamespace(is_closing=lambda: False),
    )
    client._initialize_result = {"capabilities": {}}
    with pytest.raises(LSPProtocolError, match="rename not supported"):
        await client.rename("/tmp/example.py", 0, 0, "renamed")


@pytest.mark.asyncio
async def test_rename_rejects_invalid_new_name() -> None:
    client = LSPClient(
        server_id="fake",
        workspace_root="/tmp",
        command=["unused"],
    )
    client._state = "running"
    client._proc = SimpleNamespace(
        returncode=None,
        stdin=SimpleNamespace(is_closing=lambda: False),
    )
    client._initialize_result = {"capabilities": {"renameProvider": True}}
    with pytest.raises(ValueError, match="new_name"):
        await client.rename("/tmp/example.py", 0, 0, "bad\nname")
