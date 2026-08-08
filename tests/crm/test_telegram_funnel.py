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
    from keprix.crm.store import CrmStore, reset_crm_store_for_tests
    from keprix.crm.telegram_funnel import handle_leads_command

    reset_crm_store_for_tests()
    store = CrmStore(tmp_path / "c.db")
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
