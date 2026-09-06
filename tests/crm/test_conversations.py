"""CRM conversation history and tenant isolation tests."""

from pathlib import Path

import pytest

from keprix.crm.conversations import append_message, summarize_conversation
from keprix.crm.store import reset_crm_store_for_tests


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_append_reuses_thread_and_preserves_order(store):
    first = append_message("ws-a", channel="telegram", external_chat_id="chat-1", contact_id="lead-1", body="Hello", store=store)
    append_message("ws-a", channel="telegram", external_chat_id="chat-1", contact_id="lead-1", body="Hi back", direction="outbound", store=store)
    conversation = first["conversation"]
    messages = store.list_conversation_messages("ws-a", conversation["id"])
    assert len(messages) == 2
    assert [m["direction"] for m in messages] == ["inbound", "outbound"]
    assert store.list_conversation_links("ws-a", conversation["id"])[0]["external_chat_id"] == "chat-1"


def test_same_external_id_isolated_between_workspaces(store):
    a = append_message("ws-a", channel="whatsapp", external_chat_id="same", contact_id="lead-a", body="A", store=store)
    b = append_message("ws-b", channel="whatsapp", external_chat_id="same", contact_id="lead-b", body="B", store=store)
    assert a["conversation"]["id"] != b["conversation"]["id"]
    assert store.list_conversation_messages("ws-a", b["conversation"]["id"]) == []


def test_conflicting_contact_is_rejected(store):
    append_message("ws", channel="web", external_chat_id="chat", contact_id="one", body="x", store=store)
    with pytest.raises(ValueError, match="contact_conflict"):
        append_message("ws", channel="web", external_chat_id="chat", contact_id="two", body="y", store=store)


@pytest.mark.asyncio
async def test_summary_is_stored(monkeypatch, store):
    result = append_message("ws", channel="email", external_chat_id="thread", body="Need a quote", store=store)
    monkeypatch.setattr("keprix.email.llm.llm_complete", lambda *args, **kwargs: _summary())
    summary = await summarize_conversation("ws", result["conversation"]["id"], store=store)
    assert summary["summary"] == "Customer requests a quote."


async def _summary():
    return "Customer requests a quote."
