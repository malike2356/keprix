"""Tests for OSINT enrichment (prompt 05). All mocked; never probe real people."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from keprix.crm import osint_enrich as oe
from keprix.crm.store import reset_crm_store_for_tests


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


@pytest.fixture(autouse=True)
def _enable(monkeypatch):
    monkeypatch.setenv(oe.OSINT_ENABLED_ENV, "1")
    yield


@pytest.fixture()
def _ack(store, monkeypatch):
    def _enabled(*a, **k):
        return True

    monkeypatch.setattr(oe, "_acknowledged", _enabled)


def _lead(store):
    return store.create_lead(
        "ws1",
        name="Ada Lovelace",
        emails=[{"address": "ada@analytical.engine", "primary": True}],
        company_name="Analytical Engines Ltd",
        source="fixture",
    )


def test_disabled_by_default(store, monkeypatch):
    monkeypatch.delenv(oe.OSINT_ENABLED_ENV, raising=False)
    lead = _lead(store)
    result = asyncio.run(oe.osint_enrich_lead(store, "ws1", lead["id"]))
    assert result["status"] == "disabled"


def test_requires_acknowledgement(store, monkeypatch):
    monkeypatch.setattr(oe, "_acknowledged", lambda *a, **k: False)
    lead = _lead(store)
    result = asyncio.run(oe.osint_enrich_lead(store, "ws1", lead["id"]))
    assert result["status"] == "blocked"


def test_strip_sensitive():
    data = {"ok": {"exists": True}, "recovery_email": "x@y.com", "breaches": ["leak"]}
    out = oe._strip_sensitive(data)
    assert "recovery_email" not in out
    assert "breaches" not in out
    assert out["ok"]["exists"] is True


def test_cache_key_stable():
    a = oe._cache_key("holehe", "Ada@X.com")
    b = oe._cache_key("holehe", "ada@x.com")
    assert a == b


def test_engine_available_false_for_missing():
    assert oe.engine_available("__definitely_not_installed_engine__") is False


def test_run_engine_not_configured():
    assert oe._run_engine("__missing__", ["x"]) == {
        "error": "not_configured",
        "engine": "__missing__",
    }


def test_enrich_with_mocked_engines(store, _ack):
    lead = _lead(store)
    injected = {
        "holehe": {"presence": {"github": True, "twitter": True}},
        "maigret": {
            "profiles": [{"site": "GitHub", "url": "https://github.com/ada", "status": "claimed"}]
        },
        "theharvester": {"emails": ["contact@analytical.engine"], "people": []},
    }
    result = asyncio.run(oe.osint_enrich_lead(store, "ws1", lead["id"], injected=injected))
    assert result["status"] == "done"
    updated = store.get_lead("ws1", lead["id"])
    socials = json.loads(updated["social_profiles"])
    assert socials["email_presence"]["github"] is True
    assert socials["profiles"][0]["url"] == "https://github.com/ada"
    assert socials["domain"]["emails"] == ["contact@analytical.engine"]
    assert updated["osint_status"] == "done"


def test_cache_prevents_network(store, _ack, monkeypatch):
    lead = _lead(store)
    injected = {"holehe": {"presence": {"github": True}}}
    asyncio.run(oe.osint_enrich_lead(store, "ws1", lead["id"], injected=injected))
    # second run: injected None, engine not installed -> should still find cached result
    monkeypatch.setattr(oe, "_email_presence", lambda email: {"error": "not_configured"})
    result = asyncio.run(oe.osint_enrich_lead(store, "ws1", lead["id"], injected=None))
    assert result["status"] == "done"  # served from cache, no fabricated network
