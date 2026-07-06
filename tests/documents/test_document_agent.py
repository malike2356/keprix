"""Document agent workflow tests."""

import pytest

from keprix.documents.document_agent import DocumentAgent
from keprix.documents.index_manager import DocumentIndexManager
from keprix.memory.rag.indexer import RagIndexer


@pytest.mark.asyncio
async def test_upload_build_index_and_ask_cited_question(tmp_path, monkeypatch) -> None:
    indexer = RagIndexer()
    manager = DocumentIndexManager(indexer=indexer, store_path=tmp_path / "indexes.json")
    import keprix.documents.index_manager as index_manager_module
    import keprix.documents.document_agent as document_agent_module

    monkeypatch.setattr(index_manager_module, "_manager", manager)
    monkeypatch.setattr(document_agent_module, "_agent", DocumentAgent())

    agent = DocumentAgent()
    index = agent.create_index(user_id="analyst", name="Tickets")
    await agent.upload_and_index(
        index.index_id,
        filename="ticket.txt",
        content="Customer: Ada\nTicket: T-42\nPriority: high\nPrinter outage in Building 3",
    )
    answer = await agent.ask(user_id="analyst", question="What happened in Building 3?")
    assert answer["citations"]
    assert "Building 3" in answer["answer"] or answer["citations"][0]["snippet"]

    extracted = await agent.extract(
        text="Customer: Ada\nTicket: T-42\nPriority: high\nSummary: Printer outage",
        schema_name="customer_ticket",
    )
    assert extracted["ticket_id"] or extracted["summary"]
