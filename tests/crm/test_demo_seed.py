"""Local CRM demo seed guards and idempotent seed."""

from __future__ import annotations

import os

import pytest

from keprix.crm.demo_seed import DemoSeedForbidden, assert_local_demo_seed_allowed, purge_crm_demo, seed_crm_demo


def test_demo_seed_forbidden_without_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KEPRIX_ALLOW_CRM_DEMO_SEED", raising=False)
    monkeypatch.delenv("KEPRIX_DEMO_SEED_CONFIRM", raising=False)
    with pytest.raises(DemoSeedForbidden):
        assert_local_demo_seed_allowed()


def test_demo_seed_blocked_for_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_ALLOW_CRM_DEMO_SEED", "1")
    monkeypatch.setenv("KEPRIX_DEMO_SEED_CONFIRM", "local-only")
    monkeypatch.setenv("KEPRIX_ENV", "production")
    with pytest.raises(DemoSeedForbidden):
        assert_local_demo_seed_allowed()


def test_demo_seed_creates_pipeline_models(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_ALLOW_CRM_DEMO_SEED", "1")
    monkeypatch.setenv("KEPRIX_DEMO_SEED_CONFIRM", "local-only")
    monkeypatch.setenv("KEPRIX_ENV", "local")
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("KEPRIX_INSTANCE_URL", raising=False)
    monkeypatch.delenv("KEPRIX_LIVE", raising=False)

    first = seed_crm_demo("default")
    assert first["ok"] is True
    assert first["created"].get("leads", 0) >= 1
    assert first["created"].get("accounts", 0) >= 1
    assert first["ids"].get("list_id")

    second = seed_crm_demo("default")
    assert second["ok"] is True
    # Second pass should mostly reuse
    assert second["reused"].get("leads", 0) >= 1

    from keprix.crm.store import get_crm_store

    store = get_crm_store()
    leads = store.list_leads("default", limit=50)
    stages = {str(row.get("stage")) for row in leads}
    assert "discovered" in stages
    assert "paying" in stages or "qualified" in stages
    assert store.list_accounts("default", limit=10)
    assert store.list_contacts("default", limit=10)
    assert store.list_deals("default", limit=10)
    readiness = store.list_sender_readiness("default", limit=10)
    assert any(r.get("domain") == "demo-seed.local" for r in readiness)

    purged = purge_crm_demo("default")
    assert purged["ok"] is True
    assert purged["removed"].get("leads", 0) >= 1
    assert purged["present"] is False
    assert not [r for r in store.list_leads("default", limit=50) if str(r.get("external_source_id") or "").startswith("demo-seed:")]
    readiness_after = store.list_sender_readiness("default", limit=10)
    assert not any(r.get("domain") == "demo-seed.local" for r in readiness_after)
