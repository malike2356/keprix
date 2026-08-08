"""Discovery adapter framework + job runner tests (prompt 436)."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.crm.store import reset_crm_store_for_tests
from keprix.discovery import (
    DiscoverLimits,
    DiscoverQuery,
    JobStatus,
    LeadCandidate,
    get_discovery_registry,
    get_discovery_runner,
    materialize_candidates,
    reset_discovery_registry_for_tests,
)
from keprix.discovery.adapters.fake import FakeDiscoveryAdapter
from keprix.outreach.ops import OutreachOpsStore
from keprix.outreach.store import reset_outreach_store_for_tests


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reset_outreach_store_for_tests(tmp_path / "outreach.sqlite")
    import keprix.outreach.ops as ops_mod

    ops_mod._ops = OutreachOpsStore(path=tmp_path / "outreach.sqlite")
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    monkeypatch.setenv("KEPRIX_DISCOVERY_SOFT_WALL_MATERIALIZE", "0")
    reset_discovery_registry_for_tests()
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_fake_adapter_end_to_end_creates_list(store, monkeypatch):
    reg = get_discovery_registry()
    reg.ensure_builtin()
    runner = get_discovery_runner(store=store)
    job = runner.create_job(
        "ws_a",
        "fake",
        query="Acme",
        auto_materialize=True,
        list_name="Fake draft",
    )
    result = runner.run_job("ws_a", job["id"], materialize=True, force=True)
    assert result["job"]["status"] == JobStatus.DONE
    assert result["materialize"]["list_id"]
    assert result["materialize"]["member_count"] >= 1
    assert result["deep_links"]["job"].startswith("/crm/jobs/")
    lst = store.get_list("ws_a", result["materialize"]["list_id"])
    assert lst is not None
    assert lst["status"] == "draft"


def test_failed_job_keeps_resume_cursor(store):
    reg = reset_discovery_registry_for_tests()

    class BoomAdapter(FakeDiscoveryAdapter):
        name = "boom"

        def discover(self, query, limits):
            raise RuntimeError("simulated failure")

    reg.register(BoomAdapter(), replace=True)
    # Also need fake for other tests - register boom only
    runner = get_discovery_runner(store=store)
    # Patch registry on runner
    runner._registry = reg
    job = runner.create_job("ws_a", "boom", query="x")
    # Seed checkpoint candidates then fail
    store.update_discovery_job(
        "ws_a",
        job["id"],
        checkpoint={
            "cursor": 1,
            "candidates": [
                LeadCandidate(company="Prior", source="boom", external_id="p1").to_dict()
            ],
            "attempts": 0,
        },
    )
    result = runner.run_job("ws_a", job["id"], max_retries=0)
    assert result["job"]["status"] in {JobStatus.FAILED, JobStatus.DEAD_LETTER}
    checkpoint = result["job"].get("checkpoint") or {}
    assert checkpoint.get("cursor") == 1
    assert len(checkpoint.get("candidates") or []) == 1
    assert result.get("resumable") is True


def test_adapter_not_configured_honest_error(store, monkeypatch):
    monkeypatch.delenv("COMPANIES_HOUSE_API_KEY", raising=False)
    monkeypatch.setenv("KEPRIX_COMPANIES_HOUSE_ENABLED", "1")
    reset_discovery_registry_for_tests()
    runner = get_discovery_runner(store=store)
    job = runner.create_job("ws_a", "companies_house", query="Acme")
    result = runner.run_job("ws_a", job["id"])
    assert result.get("error_code") == "not_configured"
    assert result["job"]["status"] == JobStatus.FAILED


def test_manifest_declares_licence_and_outreach_false():
    reset_discovery_registry_for_tests()
    reg = get_discovery_registry()
    reg.ensure_builtin()
    manifests = {m["name"]: m for m in reg.list_manifests()}
    fake = manifests["fake"]
    assert fake["licence_ref"]
    assert fake["outreach_allowed"] is False
    assert fake["contact_use_eligible"] is False
    assert "health" in fake["health"]["status"] or fake["health"]["status"] == "healthy"


def test_materialize_soft_wall_when_enabled(store, monkeypatch):
    monkeypatch.setenv("KEPRIX_DISCOVERY_SOFT_WALL_MATERIALIZE", "1")
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    candidates = [
        LeadCandidate(company="Soft Wall Co", source="fake", external_id="sw1", emails=["a@ex.com"])
    ]
    result = materialize_candidates(
        "ws_a",
        candidates,
        list_name="Pending",
        source="fake",
        store=store,
        force=False,
    )
    assert result["blocked"] is True
    assert result["approval"]
