"""Tests for social channel connectors (prompt 06). Decision-gated; no outbound, no scrape."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

import pytest

from keprix.crm import social_channels as sc
from keprix.crm.store import reset_crm_store_for_tests


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_providers_all_pending_by_default():
    for channel, info in sc.PROVIDERS.items():
        assert info["decision"] == "pending"
        assert not sc.channel_configured(channel)


def test_outbound_refused_when_gated():
    assert sc.send_connection_request("linkedin", "abc")["status"] == "not_configured"
    assert sc.send_message("linkedin", "abc", "hi")["status"] == "not_configured"
    assert sc.discover_leads("meta_lead_ads", {}, 5)["status"] == "not_configured"
    assert sc.list_senders("linkedin")["status"] == "not_configured"
    assert sc.list_conversations("x")["status"] == "not_configured"


def test_x_discovery_reuses_read_only_search(monkeypatch):
    monkeypatch.setattr(
        "keprix.tools.x_search_tool.x_search_tool", lambda q, limit: [{"q": q, "limit": limit}]
    )
    # x discovery capability is True; flip decision to approved to exercise the read-only path.
    monkeypatch.setitem(sc.PROVIDERS["x"], "decision", "approved")
    result = sc.discover_leads("x", {"query": "test"}, limit=3)
    assert result["ok"] is True
    assert result["results"] == [{"q": "test", "limit": 3}]


def test_meta_signature_verify():
    body = b'{"entry":[]}'
    secret = "shh"
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert sc.verify_meta_signature(body, f"sha256={digest}", secret) is True
    assert sc.verify_meta_signature(body, "sha256=deadbeef", secret) is False
    assert sc.verify_meta_signature(body, digest, secret) is False  # missing prefix
    assert sc.verify_meta_signature(body, f"sha256={digest}", "wrong") is False


def test_provider_signature_verify():
    body = b"hello"
    secret = "k"
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert sc.verify_provider_signature(body, digest, secret) is True
    assert sc.verify_provider_signature(body, "bad", secret) is False


def test_connect_stores_channel_and_connection(store):
    result = sc.connect_channel(store, "ws1", "linkedin", provider_account_id="acct-1")
    assert result["ok"] is True
    conns = sc.list_connections(store, "ws1")
    assert any(c["channel"] == "linkedin" for c in conns)


def test_record_event_replay_safe(store):
    r1 = sc.record_social_event(
        store, "ws1", "meta_lead_ads", "evt-1", "leadgen", {"field_data": []}
    )
    assert r1["status"] == "recorded"
    r2 = sc.record_social_event(
        store, "ws1", "meta_lead_ads", "evt-1", "leadgen", {"field_data": []}
    )
    assert r2["status"] == "duplicate"
    assert r2["replay_safe"] is True


def test_record_event_rejects_missing_id(store):
    r = sc.record_social_event(store, "ws1", "meta_lead_ads", "", "leadgen", {})
    assert r["ok"] is False
    assert r["status"] == "rejected"
