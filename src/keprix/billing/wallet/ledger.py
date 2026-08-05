"""Ledger operations for managed AI credits."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.billing.wallet.policy import AiWalletPolicy
from keprix.billing.wallet.store import AiCreditStore, LedgerEntry, WalletState, get_ai_credit_store


def _month_key(now: datetime | None = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return f"{dt.year:04d}-{dt.month:02d}"


def ensure_period_and_trial(
    workspace_id: str,
    policy: AiWalletPolicy,
    *,
    user_id: str | None = None,
    store: AiCreditStore | None = None,
) -> WalletState:
    """Reset monthly included credits and grant trial once when applicable."""
    credit_store = store or get_ai_credit_store()
    wallet = credit_store.get_wallet(workspace_id)
    if user_id:
        wallet.user_id = user_id

    period = _month_key()
    changed = False

    if policy.included_credits_monthly > 0 and wallet.included_period != period:
        wallet.included_remaining = int(policy.included_credits_monthly)
        wallet.included_period = period
        changed = True
        credit_store.save_wallet(wallet)
        credit_store.append_entry(
            workspace_id=workspace_id,
            entry_type="included_reset",
            credits=int(policy.included_credits_monthly),
            user_id=user_id,
            note=f"Monthly included credits for {period}",
            metadata={"period": period, "plan_id": policy.plan_id},
            apply_to_balance=False,
            apply_to_included=False,
        )
        wallet = credit_store.get_wallet(workspace_id)

    if (
        policy.deployment_mode == "hosted_trial"
        and policy.trial_credits > 0
        and int(wallet.trial_granted or 0) <= 0
    ):
        wallet.trial_granted = int(policy.trial_credits)
        wallet.balance_credits = int(wallet.balance_credits) + int(policy.trial_credits)
        credit_store.save_wallet(wallet)
        credit_store.append_entry(
            workspace_id=workspace_id,
            entry_type="grant",
            credits=int(policy.trial_credits),
            user_id=user_id,
            note="Hosted trial credit grant",
            metadata={"kind": "trial", "plan_id": policy.plan_id},
            apply_to_balance=False,
        )
        wallet = credit_store.get_wallet(workspace_id)
        changed = True

    if changed:
        return credit_store.get_wallet(workspace_id)
    if user_id and wallet.user_id != user_id:
        wallet.user_id = user_id
        return credit_store.save_wallet(wallet)
    return wallet


def grant_credits(
    workspace_id: str,
    credits: int,
    *,
    user_id: str | None = None,
    note: str | None = None,
    metadata: dict[str, Any] | None = None,
    entry_type: str = "grant",
    store: AiCreditStore | None = None,
) -> tuple[WalletState, LedgerEntry]:
    credit_store = store or get_ai_credit_store()
    amount = max(0, int(credits))
    return credit_store.append_entry(
        workspace_id=workspace_id,
        entry_type=entry_type,  # type: ignore[arg-type]
        credits=amount,
        user_id=user_id,
        note=note,
        metadata=metadata,
        apply_to_balance=True,
    )


def purchase_credits(
    workspace_id: str,
    credits: int,
    *,
    user_id: str | None = None,
    note: str | None = None,
    metadata: dict[str, Any] | None = None,
    store: AiCreditStore | None = None,
) -> tuple[WalletState, LedgerEntry]:
    return grant_credits(
        workspace_id,
        credits,
        user_id=user_id,
        note=note or "Purchased managed AI credits",
        metadata=metadata,
        entry_type="purchase",
        store=store,
    )


def refund_credits(
    workspace_id: str,
    credits: int,
    *,
    user_id: str | None = None,
    note: str | None = None,
    metadata: dict[str, Any] | None = None,
    store: AiCreditStore | None = None,
) -> tuple[WalletState, LedgerEntry]:
    return grant_credits(
        workspace_id,
        credits,
        user_id=user_id,
        note=note or "Credit refund",
        metadata=metadata,
        entry_type="refund",
        store=store,
    )


def admin_adjust(
    workspace_id: str,
    credits: int,
    *,
    user_id: str | None = None,
    note: str | None = None,
    metadata: dict[str, Any] | None = None,
    store: AiCreditStore | None = None,
) -> tuple[WalletState, LedgerEntry]:
    credit_store = store or get_ai_credit_store()
    return credit_store.append_entry(
        workspace_id=workspace_id,
        entry_type="admin_adjust",
        credits=int(credits),
        user_id=user_id,
        note=note or "Admin adjustment",
        metadata=metadata,
        apply_to_balance=True,
    )


def expire_credits(
    workspace_id: str,
    credits: int,
    *,
    user_id: str | None = None,
    note: str | None = None,
    metadata: dict[str, Any] | None = None,
    store: AiCreditStore | None = None,
) -> tuple[WalletState, LedgerEntry]:
    credit_store = store or get_ai_credit_store()
    amount = -abs(int(credits))
    wallet = credit_store.get_wallet(workspace_id)
    # Clamp so we do not expire more than available prepaid balance.
    amount = -min(abs(amount), max(0, int(wallet.balance_credits)))
    return credit_store.append_entry(
        workspace_id=workspace_id,
        entry_type="expiry",
        credits=amount,
        user_id=user_id,
        note=note or "Credit expiry",
        metadata=metadata,
        apply_to_balance=True,
    )


def debit_credits(
    workspace_id: str,
    credits: int,
    *,
    user_id: str | None = None,
    model: str | None = None,
    channel: str | None = None,
    run_id: str | None = None,
    note: str | None = None,
    metadata: dict[str, Any] | None = None,
    store: AiCreditStore | None = None,
) -> tuple[WalletState, LedgerEntry, int]:
    """Debit included allowance first, then prepaid balance.

    Returns (wallet, ledger_entry, prepaid_drawn).
    """
    credit_store = store or get_ai_credit_store()
    need = max(0, int(credits))
    wallet = credit_store.get_wallet(workspace_id)
    if user_id:
        wallet.user_id = user_id

    from_included = min(need, max(0, int(wallet.included_remaining)))
    from_balance = need - from_included

    if from_included:
        wallet.included_remaining = int(wallet.included_remaining) - from_included
    if from_balance:
        wallet.balance_credits = int(wallet.balance_credits) - from_balance
    credit_store.save_wallet(wallet)

    meta = dict(metadata or {})
    meta.update({"from_included": from_included, "from_balance": from_balance})
    wallet, entry = credit_store.append_entry(
        workspace_id=workspace_id,
        entry_type="debit",
        credits=-need,
        user_id=user_id,
        model=model,
        channel=channel,
        run_id=run_id,
        note=note or "Managed AI debit",
        metadata=meta,
        apply_to_balance=False,
        apply_to_included=False,
    )
    if need > 0:
        credit_store.add_daily_usage(workspace_id, need)
    return wallet, entry, from_balance
