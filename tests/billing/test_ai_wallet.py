"""Tests for managed AI credit wallet."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.billing.wallet.enforcer import (
    ManagedAiExhausted,
    assert_managed_call_allowed,
    check_managed_call,
    debit_managed_call,
)
from keprix.billing.wallet.policy import (
    resolve_billing_mode,
    resolve_policy,
    trusted_workspace_id,
)
from keprix.billing.wallet.pricing import credits_for_usage, pricing_for
from keprix.billing.wallet.store import AiCreditStore, reset_ai_credit_store_for_tests


@pytest.fixture
def wallet_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AiCreditStore:
    monkeypatch.setenv("KEPRIX_HOSTED", "true")
    monkeypatch.setenv("KEPRIX_BILLING_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_BILLING_PROVIDER", "stripe")
    store = AiCreditStore(sqlite_path=tmp_path / "wallet.db")
    reset_ai_credit_store_for_tests(store)
    return store


def test_unknown_model_uses_conservative_fallback():
    in_rate, out_rate, source = pricing_for("totally-unknown-model-xyz")
    assert source == "fallback"
    assert in_rate >= 10
    assert out_rate >= 50
    quote = credits_for_usage("totally-unknown-model-xyz", input_tokens=1_000_000, output_tokens=0)
    # $10 provider x 2 markup = $20 = 2000 credits
    assert quote.credits == 2000
    assert quote.pricing_source == "fallback"


def test_known_model_catalog_pricing():
    quote = credits_for_usage("gpt-4o-mini", input_tokens=1_000_000, output_tokens=0)
    # $0.15 x 2 = $0.30 = 30 credits
    assert quote.credits == 30
    assert quote.pricing_source == "catalog"


@pytest.mark.asyncio
async def test_managed_calls_debit_wallet(wallet_store: AiCreditStore, monkeypatch: pytest.MonkeyPatch):
    async def _policy(*, user_id=None, plan_id=None):
        from keprix.billing.wallet.policy import AiWalletPolicy

        return AiWalletPolicy(
            deployment_mode="pro",
            plan_id="pro",
            managed_ai_available=True,
            byok_default=False,
            included_credits_monthly=100,
            trial_credits=0,
            trial_daily_cap_credits=0,
            platform_markup=2.0,
        )

    monkeypatch.setattr("keprix.billing.wallet.enforcer.resolve_policy", _policy)

    check = await check_managed_call(
        user_id="user-1",
        workspace_id="ws-1",
        model="gpt-4o-mini",
        estimated_tokens=100,
        store=wallet_store,
    )
    assert check.allowed is True
    assert check.billing_mode == "managed"

    before = wallet_store.get_wallet("ws-1").available
    result = await debit_managed_call(
        user_id="user-1",
        workspace_id="ws-1",
        model="gpt-4o-mini",
        input_tokens=100_000,
        output_tokens=0,
        channel="web_ui",
        store=wallet_store,
    )
    assert result.billed is True
    assert result.credits > 0
    after = wallet_store.get_wallet("ws-1").available
    assert after == before - result.credits


@pytest.mark.asyncio
async def test_byok_calls_do_not_debit(wallet_store: AiCreditStore, monkeypatch: pytest.MonkeyPatch):
    async def _policy(*, user_id=None, plan_id=None):
        from keprix.billing.wallet.policy import AiWalletPolicy

        return AiWalletPolicy(
            deployment_mode="pro",
            plan_id="pro",
            managed_ai_available=True,
            byok_default=False,
            included_credits_monthly=500,
            trial_credits=0,
            trial_daily_cap_credits=0,
            platform_markup=2.0,
        )

    monkeypatch.setattr("keprix.billing.wallet.enforcer.resolve_policy", _policy)

    await check_managed_call(
        user_id="user-1",
        workspace_id="ws-byok",
        model="gpt-4o-mini",
        estimated_tokens=100,
        user_supplied_api_key=True,
        store=wallet_store,
    )
    before = wallet_store.get_wallet("ws-byok").available
    result = await debit_managed_call(
        user_id="user-1",
        workspace_id="ws-byok",
        model="gpt-4o-mini",
        input_tokens=500_000,
        output_tokens=50_000,
        user_supplied_api_key=True,
        store=wallet_store,
    )
    assert result.billed is False
    assert result.billing_mode == "byok"
    assert wallet_store.get_wallet("ws-byok").available == before


@pytest.mark.asyncio
async def test_trial_caps_prevent_overrun(wallet_store: AiCreditStore, monkeypatch: pytest.MonkeyPatch):
    async def _policy(*, user_id=None, plan_id=None):
        from keprix.billing.wallet.policy import AiWalletPolicy

        return AiWalletPolicy(
            deployment_mode="hosted_trial",
            plan_id="community",
            managed_ai_available=True,
            byok_default=False,
            included_credits_monthly=0,
            trial_credits=50,
            trial_daily_cap_credits=20,
            platform_markup=2.0,
        )

    monkeypatch.setattr("keprix.billing.wallet.enforcer.resolve_policy", _policy)

    # First call within daily cap
    ok = await check_managed_call(
        user_id="trial-user",
        workspace_id="ws-trial",
        model="gpt-4o-mini",
        estimated_tokens=10,
        store=wallet_store,
    )
    assert ok.allowed is True

    # Burn daily cap
    wallet_store.add_daily_usage("ws-trial", 20)
    blocked = await check_managed_call(
        user_id="trial-user",
        workspace_id="ws-trial",
        model="gpt-4o-mini",
        estimated_tokens=1000,
        store=wallet_store,
    )
    assert blocked.allowed is False
    assert blocked.reason == "trial_daily_cap"
    assert "byok" in (blocked.actions or [])

    with pytest.raises(ManagedAiExhausted) as exc:
        await assert_managed_call_allowed(
            user_id="trial-user",
            workspace_id="ws-trial",
            model="gpt-4o-mini",
            estimated_tokens=1000,
            store=wallet_store,
        )
    assert "BYOK" in str(exc.value) or "byok" in str(exc.value.payload.get("actions", [])).lower()


@pytest.mark.asyncio
async def test_self_hosted_is_byok_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("KEPRIX_HOSTED", raising=False)
    monkeypatch.delenv("KEPRIX_DEPLOYMENT", raising=False)
    monkeypatch.setenv("KEPRIX_BILLING_ENABLED", "false")
    monkeypatch.delenv("KEPRIX_BILLING_PROVIDER", raising=False)
    store = AiCreditStore(sqlite_path=tmp_path / "ce.db")
    reset_ai_credit_store_for_tests(store)

    policy = await resolve_policy(user_id="local")
    assert policy.managed_ai_available is False
    assert policy.byok_default is True
    mode = resolve_billing_mode(policy=policy, user_supplied_api_key=False)
    assert mode == "byok"

    result = await debit_managed_call(
        user_id="local",
        workspace_id="default",
        model="gpt-4o",
        input_tokens=10_000,
        output_tokens=10_000,
        store=store,
    )
    assert result.billed is False


def test_workspace_id_spoofing_ignored():
    # Body/query workspace must never win over auth/session context.
    ws = trusted_workspace_id(
        session_workspace_id="session-ws",
        auth_workspace_id="auth-ws",
        fallback="default",
    )
    assert ws == "auth-ws"

    ws2 = trusted_workspace_id(
        session_workspace_id="session-ws",
        auth_workspace_id=None,
        fallback="default",
    )
    assert ws2 == "session-ws"


@pytest.mark.asyncio
async def test_insufficient_credits_offers_byok(wallet_store: AiCreditStore, monkeypatch: pytest.MonkeyPatch):
    async def _policy(*, user_id=None, plan_id=None):
        from keprix.billing.wallet.policy import AiWalletPolicy

        return AiWalletPolicy(
            deployment_mode="hosted_trial",
            plan_id="community",
            managed_ai_available=True,
            byok_default=False,
            included_credits_monthly=0,
            trial_credits=5,
            trial_daily_cap_credits=0,
            platform_markup=2.0,
        )

    monkeypatch.setattr("keprix.billing.wallet.enforcer.resolve_policy", _policy)

    # Grant tiny trial then drain it
    await check_managed_call(
        user_id="u",
        workspace_id="ws-empty",
        model="gpt-4o-mini",
        estimated_tokens=1,
        store=wallet_store,
    )
    wallet = wallet_store.get_wallet("ws-empty")
    wallet.balance_credits = 0
    wallet.included_remaining = 0
    wallet_store.save_wallet(wallet)

    blocked = await check_managed_call(
        user_id="u",
        workspace_id="ws-empty",
        model="claude-opus-4",
        estimated_tokens=50_000,
        store=wallet_store,
    )
    assert blocked.allowed is False
    assert blocked.reason == "insufficient_credits"
    assert "byok" in (blocked.actions or [])
    assert "purchase_credits" in (blocked.actions or [])
