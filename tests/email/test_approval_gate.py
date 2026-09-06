"""Tests for email approval gate (prompt 11). First-contact/bulk gating via Soft Wall."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.crm.store import reset_crm_store_for_tests
from keprix.email import approval_gate as gate


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_first_contact_requires_approval(store):
    assert gate._has_prior_sent(store, "ws1", "new@example.com") is False
    requires, reason = gate.require_approval("ws1", ["new@example.com"])
    assert requires is True
    assert reason == "first_contact"


def test_bulk_requires_approval(store):
    requires, reason = gate.require_approval(
        "ws1", ["a@x.com", "b@x.com", "c@x.com", "d@x.com", "e@x.com"]
    )
    assert requires is True
    assert reason == "bulk"


def test_existing_recipient_not_gated(store):
    gate.record_sent(store, "ws1", "known@example.com")
    requires, reason = gate.require_approval("ws1", ["known@example.com"])
    assert requires is False
    assert reason == "existing_recipients"


def test_record_sent_is_idempotent(store):
    gate.record_sent(store, "ws1", "a@x.com")
    gate.record_sent(store, "ws1", "a@x.com")
    assert gate._has_prior_sent(store, "ws1", "a@x.com") is True


def test_payload_hash_is_stable():
    a = gate._payload_hash(["b@x.com", "a@x.com"], "subject", "body")
    b = gate._payload_hash(["a@x.com", "b@x.com"], "subject", "body")
    assert a == b
    c = gate._payload_hash(["a@x.com", "b@x.com"], "subject", "different body")
    assert a != c


def test_loopback_trusted():
    assert gate.is_loopback_trusted({"role": "admin", "username": "local"}) is True
    assert gate.is_loopback_trusted({"role": "user", "username": "someone"}) is False


def test_find_approved_approval_no_match_returns_none(store, monkeypatch):
    class _Ops:
        def list_approvals(self, workspace_id, status=None):
            return []

    monkeypatch.setattr("keprix.outreach.ops.get_outreach_ops_store", lambda: _Ops())
    assert gate.find_approved_approval("ws1", to_list=["a@x.com"], subject="s", body="b") is None


def test_find_approved_approval_matches_payload_hash(store, monkeypatch):
    class _Ops:
        def list_approvals(self, workspace_id, status=None):
            import json

            return [
                {
                    "id": "ap1",
                    "payload_json": json.dumps(
                        {"payload_hash": gate._payload_hash(["a@x.com"], "s", "b")}
                    ),
                }
            ]

    monkeypatch.setattr("keprix.outreach.ops.get_outreach_ops_store", lambda: _Ops())
    found = gate.find_approved_approval("ws1", to_list=["a@x.com"], subject="s", body="b")
    assert found is not None
    assert found["id"] == "ap1"
