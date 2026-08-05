"""Deeper parity tests: real wiring, not theatre."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.billing.promo import PromoStore
from keprix.billing.tenant_byok import TenantByokStore
from keprix.workflows.conditions import execute_booking_confirmed_workflow


def test_byok_aes_roundtrip(tmp_path: Path) -> None:
    store = TenantByokStore(path=tmp_path / "byok.json")
    meta = store.put(tenant_id="local", provider="openai", api_key="sk-live-secret-9999")
    assert "sk-live" not in str(meta)
    assert meta.get("cipher") == "aes-gcm"
    assert store.get_secret(tenant_id="local", provider="openai") == "sk-live-secret-9999"


def test_execute_booking_confirmed_creates_lead(tmp_path: Path, monkeypatch) -> None:
    from keprix.product_leads.store import LeadStore

    lead_store = LeadStore(path=tmp_path / "leads.json")
    monkeypatch.setattr("keprix.product_leads.store.get_lead_store", lambda: lead_store)
    result = execute_booking_confirmed_workflow(
        {
            "id": "book-1",
            "status": "confirmed",
            "guest_name": "Ada",
            "guest_email": "ada@example.com",
            "tenant_id": "local",
        }
    )
    assert result["executed"] is True
    assert result["lead"]["vical_booking_id"] == "book-1"
    assert lead_store.list_leads()


@pytest.mark.asyncio
async def test_rag_admin_lists_real_registry() -> None:
    from keprix.memory.rag_admin_routes import list_pipelines

    payload = await list_pipelines(user={"id": "u", "role": "admin"})
    assert payload["pipelines"]
    assert payload["training"]["supported"] is False
    assert payload["ui"] == "/data?tab=rag"


@pytest.mark.asyncio
async def test_governance_export_fulfills(tmp_path: Path, monkeypatch) -> None:
    from keprix.privacy.dsar import DsarStore

    store = DsarStore(base_dir=tmp_path)
    monkeypatch.setattr("keprix.privacy.dsar.get_dsar_store", lambda: store)
    monkeypatch.setattr("keprix.governance.dsar_routes.get_dsar_store", lambda: store)
    from keprix.governance.dsar_routes import request_export, DsarBody

    result = await request_export(
        DsarBody(subject_user_id="u1", fulfill_now=True),
        admin={"id": "admin", "role": "admin"},
    )
    req = result["request"]
    assert req["status"] == "completed"
    assert req.get("export_path")
    assert Path(req["export_path"]).exists()


def test_promo_checkout_trial_override(tmp_path: Path, monkeypatch) -> None:
    store = PromoStore(path=tmp_path / "promo.json")
    store.upsert("TRIAL14", trial_days=14, price_id="price_catalog")
    monkeypatch.setattr("keprix.billing.promo.get_promo_store", lambda: store)
    redeemed = store.redeem("TRIAL14", catalog_price_id="price_catalog")
    assert redeemed["ok"] is True
    assert redeemed["trial_days"] == 14
