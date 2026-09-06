from __future__ import annotations

from pathlib import Path

from keprix.billing.promo import PromoStore


def test_redemption_is_idempotent_and_code_is_redacted(tmp_path: Path):
    store = PromoStore(tmp_path / "promo_codes.json")
    store.upsert("INTERNAL50", percent_off=50)
    first = store.record_redemption(
        workspace_id="ws1", code="INTERNAL50", order_id="cs_1", amount_off=500, promo_id="promo_1"
    )
    second = store.record_redemption(
        workspace_id="ws1", code="INTERNAL50", order_id="cs_1", amount_off=500, promo_id="promo_1"
    )
    assert first == second
    assert first["code"] == "INT..."
    assert store.list_redemptions()["count"] == 1


def test_invalid_promo_is_rejected(tmp_path: Path):
    store = PromoStore(tmp_path / "promo_codes.json")
    result = store.redeem("MISSING")
    assert result == {"ok": False, "error": "invalid_promo"}
