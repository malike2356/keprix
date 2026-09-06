"""Tenant-scoped CRM conversations and regenerable summaries."""

from __future__ import annotations

from typing import Any

from keprix.crm.store import CrmStore, get_crm_store


def append_message(workspace_id: str, *, channel: str, external_chat_id: str, body: str,
                   direction: str = "inbound", contact_id: str | None = None,
                   confidence: float = 1.0, store: CrmStore | None = None) -> dict[str, Any]:
    store = store or get_crm_store()
    if direction not in {"inbound", "outbound"}:
        raise ValueError("direction must be inbound or outbound")
    if not channel.strip() or not external_chat_id.strip():
        raise ValueError("channel and external_chat_id are required")
    conversation = store.find_conversation(workspace_id, channel=channel, external_chat_id=external_chat_id)
    if not conversation:
        conversation = store.create_conversation(workspace_id, contact_id=contact_id or "", channel=channel, external_chat_id=external_chat_id)
    elif contact_id and conversation.get("contact_id") not in {"", contact_id}:
        raise ValueError("conversation_contact_conflict")
    if not store.list_conversation_links(workspace_id, conversation["id"]):
        store.add_conversation_link(workspace_id, conversation["id"], channel=channel, external_chat_id=external_chat_id, contact_id=contact_id or conversation.get("contact_id") or "", confidence=max(0.0, min(1.0, confidence)))
    message = store.add_conversation_message(workspace_id, conversation["id"], direction=direction, body=body)
    return {"conversation": store._conversation(workspace_id, conversation["id"]), "message": message}


async def summarize_conversation(workspace_id: str, conversation_id: str, *, store: CrmStore | None = None) -> dict[str, Any]:
    store = store or get_crm_store()
    conversation = store._conversation(workspace_id, conversation_id)
    if not conversation:
        raise LookupError("conversation_not_found")
    messages = store.list_conversation_messages(workspace_id, conversation_id)
    transcript = "\n".join(f"{m['direction']}: {m['body']}" for m in messages)
    from keprix.email.llm import llm_complete
    summary = await llm_complete(f"Summarize this CRM conversation in 3 concise sentences.\n{transcript[:12000]}", system="Return only the factual summary.")
    return store.save_conversation_summary(workspace_id, conversation_id, summary)
