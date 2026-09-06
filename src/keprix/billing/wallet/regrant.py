"""Idempotent managed-tier allowance grants and monthly regrant helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from keprix.billing.config_loader import load_billing_config
from keprix.billing.schema import PlanConfig
from keprix.billing.wallet.ledger import ensure_period_and_trial
from keprix.billing.wallet.policy import resolve_policy
from keprix.billing.wallet.store import AiCreditStore, LedgerEntry, WalletState, get_ai_credit_store


def _period(now: datetime | None = None) -> str:
    value = now or datetime.now(UTC)
    return f"{value.year:04d}-{value.month:02d}"


def _allowance(plan: PlanConfig) -> int:
    return max(0, int((plan.feature_flags or {}).get("ai_included_credits") or 0))


@dataclass(frozen=True)
class GrantResult:
    granted: bool
    wallet: WalletState
    entry: LedgerEntry | None
    reason: str


def grant_on_assignment(
    workspace_id: str,
    plan: PlanConfig,
    *,
    user_id: str | None = None,
    store: AiCreditStore | None = None,
) -> GrantResult:
    """Grant a managed plan allowance once for the lifetime of that tier assignment."""
    credit_store = store or get_ai_credit_store()
    wallet = credit_store.get_wallet(workspace_id)
    amount = _allowance(plan)
    managed = bool((plan.feature_flags or {}).get("managed_ai"))
    marker = f"managed-assignment:{plan.id}"
    if not managed or amount <= 0:
        return GrantResult(False, wallet, None, "plan_not_managed")
    if credit_store.has_ledger_marker(workspace_id, marker):
        return GrantResult(False, wallet, None, "already_granted")

    # Mark the current included period so the monthly worker cannot immediately
    # issue a second grant after a new assignment.
    wallet.included_period = _period()
    credit_store.save_wallet(wallet)
    wallet, entry = credit_store.append_entry(
        workspace_id=workspace_id,
        entry_type="grant",
        credits=amount,
        user_id=user_id,
        note=f"Managed {plan.id} tier allowance grant",
        metadata={"kind": "managed_tier_assignment", "plan_id": plan.id, "idempotency_key": marker},
        apply_to_balance=False,
        apply_to_included=True,
    )
    return GrantResult(True, wallet, entry, "granted")


async def regrant_monthly(
    workspace_id: str,
    plan_id: str,
    *,
    user_id: str | None = None,
    now: datetime | None = None,
    store: AiCreditStore | None = None,
) -> GrantResult:
    """Reset the existing included allowance once per month for opted-in plans."""
    credit_store = store or get_ai_credit_store()
    config = load_billing_config(force_reload=True)
    plan = config.plan_by_id(plan_id) if config else None
    wallet = credit_store.get_wallet(workspace_id)
    if plan is None or plan.regrant_cadence != "monthly" or _allowance(plan) <= 0:
        return GrantResult(False, wallet, None, "regrant_disabled")
    policy = await resolve_policy(user_id=user_id, plan_id=plan.id)
    before = credit_store.get_wallet(workspace_id)
    after = ensure_period_and_trial(workspace_id, policy, user_id=user_id, store=credit_store)
    if after.included_period != _period(now):
        return GrantResult(False, after, None, "period_not_current")
    if before.included_period == after.included_period:
        return GrantResult(False, after, None, "already_regranted")
    entries = credit_store.list_ledger(workspace_id, limit=500)
    entry = next(
        (
            item
            for item in entries
            if item.entry_type == "included_reset"
            and item.metadata.get("period") == after.included_period
            and item.metadata.get("plan_id") == plan.id
        ),
        None,
    )
    return GrantResult(True, after, entry, "regranted")


async def assignment_status(
    workspace_id: str,
    plan_id: str,
    *,
    store: AiCreditStore | None = None,
) -> dict[str, Any]:
    credit_store = store or get_ai_credit_store()
    entries = credit_store.list_ledger(workspace_id, limit=500)
    marker = f"managed-assignment:{plan_id}"
    assignment = next(
        (item for item in entries if item.metadata.get("idempotency_key") == marker), None
    )
    monthly = [
        item
        for item in entries
        if item.entry_type == "included_reset" and item.metadata.get("plan_id") == plan_id
    ]
    return {
        "plan_id": plan_id,
        "assigned": assignment is not None,
        "last_grant": assignment.to_dict() if assignment else None,
        "last_regrant": monthly[0].to_dict() if monthly else None,
    }
