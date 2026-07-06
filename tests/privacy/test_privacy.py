"""Tests for privacy stores, erasure dry_run, and GDPR health endpoint."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.privacy.consent import ConsentStore
from keprix.privacy.dsar import DsarStore
from keprix.privacy.erasure import ErasureStore, erase_user_data


@pytest.fixture()
def consent(tmp_path: Path) -> ConsentStore:
    return ConsentStore(base_dir=tmp_path)


def test_consent_record_and_list(consent: ConsentStore) -> None:
    row = consent.record(user_id="u1", purpose="analytics", granted=True, ip_hash="abc")
    assert row["granted"] is True
    assert len(consent.list_for_user("u1")) == 1


@pytest.mark.asyncio
async def test_dsar_fulfill(tmp_path: Path) -> None:
    store = DsarStore(base_dir=tmp_path)
    req = store.create(user_id="u1", request_type="access")
    fulfilled = await store.fulfill(req["id"])
    assert fulfilled["status"] == "completed"
    assert Path(fulfilled["export_path"]).exists()


# ---- dry_run erasure ----

@pytest.mark.asyncio
async def test_dry_run_returns_would_remove_key(tmp_path: Path) -> None:
    result = await erase_user_data("u1", scope="full", dry_run=True)
    assert result["dry_run"] is True
    assert "would_remove" in result
    assert "removed" not in result


@pytest.mark.asyncio
async def test_dry_run_does_not_write_audit_log(tmp_path: Path) -> None:
    store = ErasureStore(base_dir=tmp_path)
    with patch("keprix.privacy.erasure.ErasureStore", return_value=store):
        await erase_user_data("u2", scope="full", dry_run=True)
    audit_path = tmp_path / "erasures.jsonl"
    assert not audit_path.exists() or audit_path.read_text() == ""


@pytest.mark.asyncio
async def test_non_dry_run_writes_audit_log(tmp_path: Path) -> None:
    store = ErasureStore(base_dir=tmp_path)
    with patch("keprix.privacy.erasure.ErasureStore", return_value=store):
        result = await erase_user_data("u3", scope="full", dry_run=False)
    assert result["ok"] is True
    assert "audit" in result
    audit_path = tmp_path / "erasures.jsonl"
    assert audit_path.exists()


# ---- DsarStore.count_pending ----

def test_count_pending_empty(tmp_path: Path) -> None:
    store = DsarStore(base_dir=tmp_path)
    assert store.count_pending() == 0


def test_count_pending_after_create(tmp_path: Path) -> None:
    store = DsarStore(base_dir=tmp_path)
    store.create(user_id="u1", request_type="access")
    store.create(user_id="u2", request_type="access")
    assert store.count_pending() == 2


@pytest.mark.asyncio
async def test_count_pending_decreases_after_fulfill(tmp_path: Path) -> None:
    store = DsarStore(base_dir=tmp_path)
    req = store.create(user_id="u1", request_type="access")
    assert store.count_pending() == 1
    await store.fulfill(req["id"])
    assert store.count_pending() == 0


# ---- GET /api/privacy/health ----

@pytest.fixture()
def privacy_app():
    from fastapi import FastAPI
    from keprix.privacy.routes import router

    _app = FastAPI()
    _app.include_router(router)
    return _app


@pytest.mark.asyncio
async def test_gdpr_health_returns_ok(privacy_app) -> None:
    async with AsyncClient(transport=ASGITransport(app=privacy_app), base_url="http://test") as client:
        response = await client.get("/api/privacy/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "pending_dsars" in data
    assert "last_retention_run" in data


@pytest.mark.asyncio
async def test_gdpr_health_last_retention_run_updates() -> None:
    from keprix.privacy.retention import apply_retention_policies, get_last_retention_run

    assert get_last_retention_run() is None or isinstance(get_last_retention_run(), str)
    await apply_retention_policies()
    assert get_last_retention_run() is not None


def test_retention_policy_round_trip(tmp_path, monkeypatch) -> None:
    from keprix.privacy import retention as retention_module

    monkeypatch.setattr(retention_module, "_privacy_dir", lambda: tmp_path)
    row = retention_module.set_retention_policy(
        "run_logs",
        retain_days=120,
        action="delete",
    )
    assert row["data_category"] == "run_logs"
    policies = retention_module.get_retention_policies()
    assert any(p["data_category"] == "run_logs" and p["retain_days"] == 120 for p in policies)
