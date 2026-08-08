"""CRM agent tools: R/W, Soft Wall, ask-data, workspace isolation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.crm.ask import ask_crm, format_telegram_reply
from keprix.crm.store import reset_crm_store_for_tests
from keprix.outreach.ops import OutreachOpsStore
from keprix.outreach.store import reset_outreach_store_for_tests


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reset_outreach_store_for_tests(tmp_path / "outreach.sqlite")
    import keprix.outreach.ops as ops_mod

    ops_mod._ops = OutreachOpsStore(path=tmp_path / "outreach.sqlite")
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def _j(raw: str) -> dict:
    return json.loads(raw)


def test_tools_registered() -> None:
    import keprix.tools.crm_tools  # noqa: F401
    from tools.registry import registry

    for name in (
        "crm_search",
        "crm_get",
        "crm_upsert_lead",
        "crm_upsert_contact",
        "crm_add_activity",
        "crm_list_create",
        "crm_list_add_members",
        "crm_set_stage",
        "crm_ask",
        "crm_suppress",
        "discovery_run",
    ):
        assert name in registry._tools, f"missing tool {name}"
        assert registry._tools[name].toolset == "crm"


def test_search_upsert_ask_and_citations(store) -> None:
    from keprix.tools import crm_tools as tools

    lead = _j(
        tools.crm_upsert_lead(
            {
                "workspace_id": "ws_a",
                "name": "Pipe lead",
                "email": "pipe@example.com",
                "stage": "listed",
                "tags": ["plumbing"],
                "domain_pack": "plumbing",
            }
        )
    )["lead"]
    assert lead["id"]

    search = _j(
        tools.crm_search(
            {"workspace_id": "ws_a", "entity": "leads", "tag": "plumbing", "q": "pipe"}
        )
    )
    assert search["count"] >= 1
    assert search["citations"][0]["id"] == lead["id"]

    ask = _j(
        tools.crm_ask(
            {
                "workspace_id": "ws_a",
                "question": "how many open leads in plumbing ICP?",
                "entity": "leads",
            }
        )
    )
    assert ask["invented"] is False
    assert ask["count"] >= 1
    assert any(c["id"] == lead["id"] for c in ask["citations"])
    assert lead["id"] in ask["answer"]

    # Direct ask helper also cites ids and never invents.
    direct = ask_crm(
        store,
        "ws_a",
        question="how many open leads in plumbing ICP?",
        tag="plumbing",
        open_only=True,
    )
    assert direct["count"] >= 1
    assert all(c.get("id") for c in direct["citations"])


def test_cross_workspace_fail_closed(store) -> None:
    from keprix.tools import crm_tools as tools

    lead = _j(
        tools.crm_upsert_lead(
            {"workspace_id": "ws_a", "name": "Secret", "email": "a@example.com"}
        )
    )["lead"]

    missing = _j(tools.crm_get({"workspace_id": "ws_b", "entity_type": "lead", "entity_id": lead["id"]}))
    assert "error" in missing
    assert missing.get("error_code") == "crm_not_found"

    ask_b = _j(tools.crm_ask({"workspace_id": "ws_b", "question": "how many leads?"}))
    assert ask_b["count"] == 0
    assert ask_b["citations"] == []

    # Cannot add foreign workspace member to local list.
    lst = _j(tools.crm_list_create({"workspace_id": "ws_b", "name": "B list"}))["list"]
    denied = _j(
        tools.crm_list_add_members(
            {
                "workspace_id": "ws_b",
                "list_id": lst["id"],
                "member_type": "lead",
                "member_id": lead["id"],
            }
        )
    )
    assert denied.get("error_code") == "cross_workspace_denied"


def test_soft_wall_delete_paying_mass_and_suppress_undo(store) -> None:
    from keprix.tools import crm_tools as tools

    lead = _j(
        tools.crm_upsert_lead(
            {"workspace_id": "ws_a", "name": "Gate me", "email": "g@example.com", "stage": "qualified"}
        )
    )["lead"]

    # Delete requires Soft Wall.
    blocked_del = _j(
        tools.crm_upsert_lead(
            {"workspace_id": "ws_a", "lead_id": lead["id"], "delete": True}
        )
    )
    assert blocked_del.get("blocked") is True
    assert blocked_del.get("error_code") == "soft_wall_required"
    assert store.get_lead("ws_a", lead["id"]) is not None

    # Stage to paying requires Soft Wall.
    blocked_pay = _j(
        tools.crm_set_stage(
            {
                "workspace_id": "ws_a",
                "entity_type": "lead",
                "entity_id": lead["id"],
                "stage": "paying",
            }
        )
    )
    assert blocked_pay.get("blocked") is True
    assert blocked_pay.get("error_code") == "soft_wall_required"
    assert store.get_lead("ws_a", lead["id"])["stage"] == "qualified"

    # Force bypass for non-paying single update works.
    moved = _j(
        tools.crm_set_stage(
            {
                "workspace_id": "ws_a",
                "entity_type": "lead",
                "entity_id": lead["id"],
                "stage": "engaged",
            }
        )
    )
    assert moved["count"] == 1
    assert moved["items"][0]["stage"] == "engaged"

    # Mass update Soft Wall.
    l2 = _j(
        tools.crm_upsert_lead(
            {"workspace_id": "ws_a", "name": "Two", "email": "two@example.com"}
        )
    )["lead"]
    blocked_mass = _j(
        tools.crm_set_stage(
            {
                "workspace_id": "ws_a",
                "entity_type": "lead",
                "ids": [lead["id"], l2["id"]],
                "stage": "listed",
            }
        )
    )
    assert blocked_mass.get("blocked") is True

    # Suppress add OK; undo Soft Wall.
    supp = _j(
        tools.crm_suppress(
            {
                "workspace_id": "ws_a",
                "address": "g@example.com",
                "subject_type": "lead",
                "subject_id": lead["id"],
            }
        )
    )
    assert supp["suppression"]["address"] == "g@example.com"
    blocked_undo = _j(
        tools.crm_suppress(
            {
                "workspace_id": "ws_a",
                "action": "undo",
                "suppression_id": supp["suppression"]["id"],
            }
        )
    )
    assert blocked_undo.get("blocked") is True

    # force=true allows delete
    deleted = _j(
        tools.crm_upsert_lead(
            {"workspace_id": "ws_a", "lead_id": lead["id"], "delete": True, "force": True}
        )
    )
    assert deleted.get("deleted") is True
    assert store.get_lead("ws_a", lead["id"]) is None


def test_list_activity_and_telegram_format(store) -> None:
    from keprix.tools import crm_tools as tools

    lead = _j(
        tools.crm_upsert_lead(
            {"workspace_id": "ws_a", "name": "Act", "email": "act@example.com"}
        )
    )["lead"]
    lst = _j(tools.crm_list_create({"workspace_id": "ws_a", "name": "Batch"}))["list"]
    member = _j(
        tools.crm_list_add_members(
            {
                "workspace_id": "ws_a",
                "list_id": lst["id"],
                "member_type": "lead",
                "member_id": lead["id"],
            }
        )
    )
    assert member["count"] == 1

    act = _j(
        tools.crm_add_activity(
            {
                "workspace_id": "ws_a",
                "entity_type": "lead",
                "entity_id": lead["id"],
                "activity_type": "note",
                "body": "Called about ICP",
                "channel": "phone",
            }
        )
    )
    assert act["activity"]["entity_id"] == lead["id"]
    assert "telegram_reply" in act

    short = format_telegram_reply("**bold** and long " + ("x" * 4000), max_len=100)
    assert len(short) <= 100
    assert "truncated" in short
    assert "**" not in short


def test_workspace_id_required(store) -> None:
    from keprix.tools import crm_tools as tools

    assert "error" in _j(tools.crm_search({}))
    assert "error" in _j(tools.crm_ask({"question": "how many leads?"}))
