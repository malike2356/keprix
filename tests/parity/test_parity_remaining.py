"""Promo, BYOK, workflows, self-knowledge parity docs."""

from __future__ import annotations

from pathlib import Path

from keprix.billing.promo import PromoStore
from keprix.billing.tenant_byok import TenantByokStore
from keprix.self_knowledge.documents import generate_all_documents
from keprix.workflows.conditions import dry_run_booking_confirmed, eval_condition


def test_promo_redeem(tmp_path: Path) -> None:
    store = PromoStore(path=tmp_path / "promos.json")
    store.upsert("SAVE10", percent_off=10, trial_days=7, price_id="price_existing")
    ok = store.redeem("save10", catalog_price_id="price_existing")
    assert ok["ok"] is True
    assert ok["trial_days"] == 7
    bad = store.redeem("NOPE")
    assert bad["ok"] is False


def test_byok_hides_secret(tmp_path: Path) -> None:
    store = TenantByokStore(path=tmp_path / "byok.json")
    meta = store.put(tenant_id="local", provider="openai", api_key="sk-secret-value")
    assert "sk-secret" not in str(meta)
    assert meta["hint"].endswith("alue")
    assert store.get_secret(tenant_id="local", provider="openai") == "sk-secret-value"
    public = store.public_status(tenant_id="local")
    assert "sk-secret-value" not in str(public)


def test_workflow_dry_run() -> None:
    assert eval_condition({"op": "eq", "field": "status", "value": "confirmed"}, {"status": "confirmed"})
    result = dry_run_booking_confirmed(
        {"status": "confirmed", "guest_name": "Ada", "guest_email": "a@b.c", "id": "b1"}
    )
    assert result["matched"] is True
    assert result["actions"]


def test_parity_guides_in_documents() -> None:
    titles = {d.title for d in generate_all_documents()}
    assert any("tenancy" in t.lower() or "Tenancy" in t for t in titles)
    assert sum(1 for d in generate_all_documents() if d.category == "parity") >= 10
