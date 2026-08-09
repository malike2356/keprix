"""Outreach workspace isolation (Prompt 622)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from keprix.outreach.ops import OutreachOpsStore
from keprix.outreach.store import OutreachStore, reset_outreach_store_for_tests


@pytest.fixture()
def outreach(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("KEPRIX_CRM_BACKEND", "sqlite")
    monkeypatch.delenv("KEPRIX_CRM_FORCE_PG", raising=False)
    path = tmp_path / "outreach.sqlite"
    store = reset_outreach_store_for_tests(path)
    ops = OutreachOpsStore(path=path)
    return store, ops


def test_outreach_lead_list_cross_workspace_fail_closed(outreach) -> None:
    store, ops = outreach
    store.create_campaign("ws_a", "A camp")
    leads = store.add_leads("ws_a", [{"email": "a@example.com", "first_name": "A"}])
    lead_id = leads[0]["id"]
    lst = ops.create_list("ws_a", "Targets")
    ops.add_list_members("ws_a", lst["id"], [lead_id])

    assert store.get_lead("ws_b", lead_id) is None
    assert store.list_leads("ws_b") == []
    assert ops.add_list_members("ws_b", lst["id"], [lead_id]) is None
    assert ops.list_lists("ws_b") == []
    # Owning workspace still intact
    assert store.get_lead("ws_a", lead_id)["email"] == "a@example.com"
    assert any(x["id"] == lst["id"] for x in ops.list_lists("ws_a"))


def test_enrollment_carries_workspace_id(outreach) -> None:
    store, _ops = outreach
    store.create_sequence("ws_a", "Seq", steps=[{"body": "hi", "delay_hours": 1}])
    seq = store.list_sequences("ws_a")[0]
    lead = store.add_leads("ws_a", [{"email": "e@example.com"}])[0]
    enr = store.enroll_lead(lead["id"], seq["id"], workspace_id="ws_a")
    assert enr["workspace_id"] == "ws_a"
    assert store.get_enrollment(enr["id"], workspace_id="ws_b") is None
    assert store.get_enrollment(enr["id"], workspace_id="ws_a") is not None


def _pg_url() -> str:
    return (
        os.environ.get("KEPRIX_TEST_DATABASE_URL")
        or "postgresql+asyncpg://keprix:changeme@127.0.0.1:5432/keprix"
    )


def _postgres_available() -> bool:
    from keprix.crm.pg_compat import ping_postgres, reset_sync_engine_for_tests

    reset_sync_engine_for_tests()
    return ping_postgres(_pg_url())


@pytest.mark.skipif(not _postgres_available(), reason="Postgres not available")
def test_outreach_pg_workspace_isolation(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_CRM_BACKEND", "postgres")
    monkeypatch.setenv("KEPRIX_CRM_FORCE_PG", "1")
    monkeypatch.setenv("KEPRIX_DATABASE_URL", _pg_url())
    monkeypatch.setenv("KEPRIX_TEST_DATABASE_URL", _pg_url())

    from keprix.config.settings import get_settings
    from keprix.crm.pg_compat import reset_sync_engine_for_tests

    get_settings.cache_clear()
    reset_sync_engine_for_tests()
    reset_outreach_store_for_tests()

    store = OutreachStore()
    assert store.backend == "postgres"
    store.add_leads("ws_out_a", [{"email": "oa@example.com"}])
    assert store.list_leads("ws_out_b") == []
    assert store.list_leads("ws_out_a")
    store.close()
