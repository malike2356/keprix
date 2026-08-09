"""email_ingest enabled path with mocked IMAP attachments (Prompt 627)."""

from __future__ import annotations

import pytest

from keprix.sheet_preprocess import email_ingest
from keprix.crm.store import reset_crm_store_for_tests
from keprix.outreach.ops import reset_outreach_ops_store_for_tests
from keprix.outreach.store import reset_outreach_store_for_tests


@pytest.fixture()
def env(tmp_path, monkeypatch):
    reset_outreach_store_for_tests(tmp_path / "outreach.db")
    reset_outreach_ops_store_for_tests(tmp_path / "outreach.db")
    store = reset_crm_store_for_tests(tmp_path / "crm.db")
    monkeypatch.setattr("keprix.crm.store.get_crm_store", lambda: store)
    monkeypatch.setenv("KEPRIX_SHEET_PREPROCESS_DIR", str(tmp_path / "sheets"))
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    return store


def test_disabled_by_default(env, monkeypatch):
    monkeypatch.delenv("KEPRIX_SHEET_EMAIL_INGEST", raising=False)
    result = email_ingest.poll_once(workspace_id="ws")
    assert result["skipped"] is True
    assert result["reason"] == "email_ingest_disabled"


def test_enabled_mocked_attachments(env, monkeypatch):
    monkeypatch.setenv("KEPRIX_SHEET_EMAIL_INGEST", "1")

    def _fetch(_account):
        return [
            {
                "from_address": "partner@example.com",
                "subject": "Leads sheet",
                "attachments": [
                    {
                        "filename": "leads.csv",
                        "content": b"company_name,email\nGamma,g@example.com\n",
                    }
                ],
            }
        ]

    result = email_ingest.poll_once(
        workspace_id="ws_mail",
        fetch_messages=_fetch,
        accounts=[{"id": "acct1", "username": "u"}],
        mode="propose",
    )
    assert result.get("skipped") is False
    assert result.get("count", 0) >= 1
    item = result["ingested"][0]
    assert item.get("upload", {}).get("upload_id")
    assert item.get("job")
    assert item.get("soft_wall", {}).get("blocked") is True
