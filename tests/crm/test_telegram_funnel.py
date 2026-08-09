"""Telegram CRM funnel intent tests (prompt 446)."""

from __future__ import annotations

import pytest

from keprix.crm.telegram_funnel import assert_channel_authz, parse_leads_intent
from keprix.slash.schemas import SlashContext


def test_parse_find_and_ask() -> None:
    assert parse_leads_intent("find plumbers in Leeds")["intent"] == "find"
    assert parse_leads_intent("/leads find plumbers in Leeds")["location"].lower() == "leeds"
    assert parse_leads_intent('/crm ask who is engaged?')["intent"] == "crm_ask"
    assert parse_leads_intent("/leads digest weekly")["intent"] == "digest"
    assert parse_leads_intent("/leads import_sheet")["intent"] == "import_sheet"
    assert parse_leads_intent("/leads enrich")["intent"] == "enrich"
    assert parse_leads_intent("/leads add_to_list Hot")["intent"] == "add_to_list"
    assert parse_leads_intent("/leads draft_campaign")["intent"] == "draft_campaign"
    assert parse_leads_intent("/leads digest_outcomes")["intent"] == "digest_outcomes"
    assert parse_leads_intent("/leads approve abc")["intent"] == "approve"


def test_unauthorized_chat_denied() -> None:
    ctx = SlashContext(
        user_id="anonymous",
        workspace_id="ws",
        channel="telegram",
        channel_user_id="999",
        raw_text="/leads digest",
        command="leads",
        role="operator",
    )
    denied = assert_channel_authz(ctx)
    assert denied is not None
    assert denied.ok is False


@pytest.mark.asyncio
async def test_digest_for_linked_user(tmp_path, monkeypatch) -> None:
    from keprix.crm.store import reset_crm_store_for_tests
    from keprix.crm.telegram_funnel import handle_leads_command

    store = reset_crm_store_for_tests(tmp_path / "c.db")
    monkeypatch.setattr("keprix.crm.store.get_crm_store", lambda: store)
    ctx = SlashContext(
        user_id="user-1",
        workspace_id="ws446",
        channel="telegram",
        channel_user_id="111",
        raw_text="/leads digest",
        command="leads",
        args=["digest"],
        role="operator",
    )
    result = await handle_leads_command(ctx)
    assert result.ok is True
    assert "CRM digest" in result.message
