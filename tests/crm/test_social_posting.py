"""Tests for social organic posting (prompt 07). Decision-gated; no live publish, no fabricated ids."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.crm import social_posting as sp
from keprix.crm.store import reset_crm_store_for_tests


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_publish_unknown_channel():
    r = sp.publish("myspace", "hello")
    assert r["status"] == "unsupported"


def test_publish_pending_approval_by_default():
    for channel in ("meta", "linkedin", "x"):
        r = sp.publish(channel, "hello world")
        assert r["status"] in {"pending_approval", "not_configured"}, channel
        assert r["external_post_id"] == ""
        assert r["public_url"] == ""


def test_publish_approved_but_no_credentials(monkeypatch):
    monkeypatch.setitem(sp.POSTING_DECISIONS["meta"], "decision", "approved")
    r = sp.publish("meta", "hello", workspace_id=None)
    assert r["status"] == "not_configured"
    assert r["external_post_id"] == ""


def test_no_fabricated_post_id():
    r = sp.publish("linkedin", "post")
    assert r["external_post_id"] == ""
    assert r["public_url"] == ""


def test_scopes_are_verified_not_self_granted():
    scopes = sp.supported_scopes()
    assert "pages_manage_posts" in scopes["meta"]
    assert "w_member_social" in scopes["linkedin"]
    assert "tweet.write" in scopes["x"]


def test_record_publish_result_isolates_failure(store):
    result = sp.publish("meta", "hello")
    rec = sp.record_publish_result(store, "ws1", "meta", result, scheduled_post_id="cal-1")
    assert rec["ok"] is True
    assert rec["status"] == result["status"]


def test_x_creds_distinct_from_xai(monkeypatch):
    # XAI_API_KEY must never satisfy X Developer Platform posting creds.
    monkeypatch.setenv("XAI_API_KEY", "xai-search-key")
    monkeypatch.setitem(sp.POSTING_DECISIONS["x"], "decision", "approved")
    r = sp.publish("x", "tweet", workspace_id=None)
    assert r["status"] == "not_configured"  # X_API_KEY/X_API_SECRET still missing
