import pytest
from pathlib import Path

from keprix.brain.node_resolvers import NodeResolver


@pytest.mark.asyncio
async def test_node_resolver_returns_seeded_content_and_tombstone() -> None:
    resolver = NodeResolver()
    resolver.seed(
        "workspace-1",
        "memory",
        "mem-1",
        {"content": "Client prefers PDF invoices on the first day.", "metadata": {"source": "note"}},
    )

    node = await resolver.resolve("workspace-1", "memory", "mem-1")
    missing = resolver.tombstone("memory", "missing")
    tool = await resolver.resolve("workspace-1", "tool", "calendar_book")

    assert node is not None
    assert node.label.startswith("Client prefers")
    assert node.metadata["source"] == "note"
    assert missing.deleted is True
    assert tool is not None
    assert tool.metadata["registry"] == "builtin"


@pytest.mark.asyncio
async def test_node_resolver_reads_vault_conversation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    session_id = "sess-vault-1"
    note = tmp_path / ".keprix" / "vault" / "conversations" / "2026" / "07" / f"{session_id}.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "---\ntitle: Mutation chat\nsession_id: sess-vault-1\n---\n# Mutation chat\n\nhello\n",
        encoding="utf-8",
    )

    node = await NodeResolver().resolve("default", "session", session_id)
    assert node is not None
    assert node.deleted is False
    assert node.label == "Mutation chat"
    assert node.metadata["source"] == "vault"
