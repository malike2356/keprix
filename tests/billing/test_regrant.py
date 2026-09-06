from __future__ import annotations

from pathlib import Path

import pytest

from keprix.billing.schema import PlanConfig
from keprix.billing.wallet.regrant import assignment_status, grant_on_assignment, regrant_monthly
from keprix.billing.wallet.store import AiCreditStore


def managed_plan(cadence: str = "monthly") -> PlanConfig:
    return PlanConfig(
        id="team",
        name="Team",
        regrant_cadence=cadence,
        feature_flags={"managed_ai": True, "ai_included_credits": 100},
    )


def test_assignment_grant_is_idempotent_and_downgrade_does_not_claw_back(tmp_path: Path) -> None:
    store = AiCreditStore(tmp_path / "wallet.db")
    plan = managed_plan()
    first = grant_on_assignment("ws-1", plan, user_id="u-1", store=store)
    second = grant_on_assignment("ws-1", plan, user_id="u-1", store=store)

    assert first.granted is True
    assert second.reason == "already_granted"
    assert store.get_wallet("ws-1").included_remaining == 100
    assert len(store.list_ledger("ws-1")) == 1


@pytest.mark.asyncio
async def test_monthly_regrant_uses_existing_included_reset_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = type("Config", (), {"plan_by_id": lambda self, _plan_id: managed_plan()})()
    monkeypatch.setattr("keprix.billing.wallet.regrant.load_billing_config", lambda force_reload=False: config)
    async def fake_policy(*, user_id=None, plan_id=None):
        from keprix.billing.wallet.policy import AiWalletPolicy

        return AiWalletPolicy("pro", "team", True, False, 100, 0, 0, 2.0)

    monkeypatch.setattr("keprix.billing.wallet.regrant.resolve_policy", fake_policy)
    store = AiCreditStore(tmp_path / "wallet.db")
    first = await regrant_monthly("ws-2", "team", user_id="u-2", store=store)
    second = await regrant_monthly("ws-2", "team", user_id="u-2", store=store)

    assert first.granted is True
    assert second.reason == "already_regranted"
    assert store.get_wallet("ws-2").included_remaining == 100
    status = await assignment_status("ws-2", "team", store=store)
    assert status["last_regrant"] is not None
