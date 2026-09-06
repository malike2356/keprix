"""Email batch build and send safety tests."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from keprix.crm.store import reset_crm_store_for_tests
from keprix.email.batch import build_batch, send_batch
from keprix.email.store import get_email_store, reset_email_store


@pytest.fixture()
def stores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    crm = reset_crm_store_for_tests(tmp_path / "crm.sqlite")
    reset_email_store()
    monkeypatch.setattr("keprix.email.batch.get_crm_store", lambda: crm)
    monkeypatch.setattr("keprix.email.batch.get_email_store", get_email_store)
    return crm, get_email_store()


@pytest.mark.asyncio
async def test_build_deduplicates_and_filters_suppressed(stores):
    crm, _ = stores
    first = crm.create_lead("ws", name="A", emails=[{"address": "a@example.com"}])
    second = crm.create_lead("ws", name="B", emails=[{"address": "a@example.com"}])
    suppressed = crm.create_lead("ws", name="C", emails=[{"address": "c@example.com"}])
    crm.create_suppression_entry("ws", channel="email", address="c@example.com", reason="unsubscribe")
    batch = await build_batch("ws", name="Weekly", lead_ids=[first["id"], second["id"], suppressed["id"]], subject="Hello", body="Body")
    assert [s.recipient for s in batch.sends] == ["a@example.com", "c@example.com"]
    assert batch.sends[1].status == "skipped_opted_out"


@pytest.mark.asyncio
async def test_send_rechecks_opt_out_and_marks_failed(monkeypatch, stores):
    crm, email = stores
    lead = crm.create_lead("ws", name="A", emails=[{"address": "a@example.com"}])
    batch = await build_batch("ws", name="Weekly", lead_ids=[lead["id"]], subject="Hello", body="Body")
    crm.create_suppression_entry("ws", channel="email", address="a@example.com", reason="unsubscribe")
    account = SimpleNamespace(email_address="sender@example.com", user_id="ws")
    email._accounts["acct"] = account
    monkeypatch.setattr("keprix.email.batch.resolve_account_connection", lambda _: _async_value(object()))
    monkeypatch.setattr("keprix.email.batch.send_smtp_message", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("smtp down")))
    result = await send_batch("ws", batch.id, account_id="acct", user={"role": "admin", "username": "local"})
    assert result["sent"] == 0
    assert result["batch"]["sends"][0]["status"] == "skipped_opted_out"


async def _async_value(value):
    return value
