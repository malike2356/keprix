"""Pre-call gate and post-call debit for managed AI usage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keprix.billing.wallet import ledger as wallet_ledger
from keprix.billing.wallet.policy import (
    AiWalletPolicy,
    BillingMode,
    resolve_billing_mode,
    resolve_policy,
    trusted_workspace_id,
)
from keprix.billing.wallet.pricing import credits_for_usage, estimate_credits_for_tokens, quote_to_dict
from keprix.billing.wallet.store import AiCreditStore, WalletState, get_ai_credit_store


class ManagedAiExhausted(RuntimeError):
    """Managed credits exhausted; product stays available via BYOK or top-up."""

    def __init__(self, message: str, *, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


@dataclass
class WalletCheckResult:
    allowed: bool
    billing_mode: BillingMode
    reason: str = ""
    available_credits: int = 0
    estimated_credits: int = 0
    actions: list[str] | None = None
    policy: AiWalletPolicy | None = None
    wallet: WalletState | None = None
    status_code: int = 402

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "billing_mode": self.billing_mode,
            "reason": self.reason,
            "available_credits": self.available_credits,
            "estimated_credits": self.estimated_credits,
            "actions": list(self.actions or []),
            "policy": self.policy.to_dict() if self.policy else None,
            "wallet": self.wallet.to_dict() if self.wallet else None,
            "status_code": self.status_code,
        }


@dataclass
class WalletDebitResult:
    billed: bool
    billing_mode: BillingMode
    credits: int = 0
    quote: dict[str, Any] | None = None
    wallet: WalletState | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "billed": self.billed,
            "billing_mode": self.billing_mode,
            "credits": self.credits,
            "quote": self.quote,
            "wallet": self.wallet.to_dict() if self.wallet else None,
        }


async def check_managed_call(
    *,
    user_id: str | None,
    workspace_id: str | None = None,
    session_workspace_id: str | None = None,
    auth_workspace_id: str | None = None,
    model: str | None = None,
    estimated_tokens: int = 0,
    user_supplied_api_key: bool = False,
    force_managed: bool | None = None,
    store: AiCreditStore | None = None,
) -> WalletCheckResult:
    """Gate a managed LLM call. BYOK always passes without debiting."""
    credit_store = store or get_ai_credit_store()
    ws = trusted_workspace_id(
        session_workspace_id=session_workspace_id or workspace_id,
        auth_workspace_id=auth_workspace_id,
    )
    policy = await resolve_policy(user_id=user_id)
    mode = resolve_billing_mode(
        policy=policy,
        user_supplied_api_key=user_supplied_api_key,
        force_managed=force_managed,
    )

    if mode == "byok":
        return WalletCheckResult(
            allowed=True,
            billing_mode="byok",
            reason="byok_no_debit",
            policy=policy,
        )

    wallet = wallet_ledger.ensure_period_and_trial(
        ws,
        policy,
        user_id=user_id,
        store=credit_store,
    )
    estimated = estimate_credits_for_tokens(model, estimated_tokens) if estimated_tokens else 1

    if policy.trial_daily_cap_credits > 0:
        used_today = credit_store.get_daily_usage(ws)
        if used_today + estimated > policy.trial_daily_cap_credits:
            return WalletCheckResult(
                allowed=False,
                billing_mode="managed",
                reason="trial_daily_cap",
                available_credits=wallet.available,
                estimated_credits=estimated,
                actions=["byok", "wait_until_tomorrow", "purchase_credits"],
                policy=policy,
                wallet=wallet,
            )

    if wallet.spend_limit_credits is not None:
        # spend_limit applies to prepaid overage only; included is free.
        # When included is zero and balance draw would exceed limit, block.
        overage_available = max(0, int(wallet.balance_credits))
        if wallet.included_remaining <= 0 and overage_available <= 0:
            pass  # fall through to available check
        elif (
            wallet.included_remaining <= 0
            and wallet.spend_limit_credits is not None
            and estimated > max(0, int(wallet.spend_limit_credits))
        ):
            return WalletCheckResult(
                allowed=False,
                billing_mode="managed",
                reason="spend_limit",
                available_credits=wallet.available,
                estimated_credits=estimated,
                actions=["raise_spend_limit", "byok", "purchase_credits"],
                policy=policy,
                wallet=wallet,
            )

    if wallet.available < estimated:
        return WalletCheckResult(
            allowed=False,
            billing_mode="managed",
            reason="insufficient_credits",
            available_credits=wallet.available,
            estimated_credits=estimated,
            actions=["byok", "purchase_credits", "upgrade"],
            policy=policy,
            wallet=wallet,
        )

    return WalletCheckResult(
        allowed=True,
        billing_mode="managed",
        reason="ok",
        available_credits=wallet.available,
        estimated_credits=estimated,
        policy=policy,
        wallet=wallet,
    )


async def debit_managed_call(
    *,
    user_id: str | None,
    workspace_id: str | None = None,
    session_workspace_id: str | None = None,
    auth_workspace_id: str | None = None,
    model: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    channel: str | None = None,
    run_id: str | None = None,
    user_supplied_api_key: bool = False,
    force_managed: bool | None = None,
    store: AiCreditStore | None = None,
) -> WalletDebitResult:
    """Debit wallet after a managed call. BYOK returns billed=False."""
    credit_store = store or get_ai_credit_store()
    ws = trusted_workspace_id(
        session_workspace_id=session_workspace_id or workspace_id,
        auth_workspace_id=auth_workspace_id,
    )
    policy = await resolve_policy(user_id=user_id)
    mode = resolve_billing_mode(
        policy=policy,
        user_supplied_api_key=user_supplied_api_key,
        force_managed=force_managed,
    )
    if mode == "byok":
        return WalletDebitResult(billed=False, billing_mode="byok")

    quote = credits_for_usage(model, input_tokens=input_tokens, output_tokens=output_tokens)
    if quote.credits <= 0:
        wallet = credit_store.get_wallet(ws)
        return WalletDebitResult(
            billed=False,
            billing_mode="managed",
            credits=0,
            quote=quote_to_dict(quote),
            wallet=wallet,
        )

    wallet_ledger.ensure_period_and_trial(ws, policy, user_id=user_id, store=credit_store)
    wallet, _entry, _drawn = wallet_ledger.debit_credits(
        ws,
        quote.credits,
        user_id=user_id,
        model=model,
        channel=channel,
        run_id=run_id,
        metadata={"pricing_source": quote.pricing_source},
        store=credit_store,
    )
    return WalletDebitResult(
        billed=True,
        billing_mode="managed",
        credits=quote.credits,
        quote=quote_to_dict(quote),
        wallet=wallet,
    )


async def assert_managed_call_allowed(**kwargs: Any) -> WalletCheckResult:
    """Raise ManagedAiExhausted when a managed call must not proceed."""
    result = await check_managed_call(**kwargs)
    if result.allowed:
        return result
    raise ManagedAiExhausted(
        (
            "Managed AI credits exhausted. Connect your own API key (BYOK) to keep "
            "using Keprix, or purchase managed tokens."
        ),
        payload=result.to_dict(),
    )


async def wallet_status(
    *,
    user_id: str | None,
    workspace_id: str | None = None,
    store: AiCreditStore | None = None,
) -> dict[str, Any]:
    credit_store = store or get_ai_credit_store()
    ws = trusted_workspace_id(session_workspace_id=workspace_id)
    policy = await resolve_policy(user_id=user_id)
    wallet = wallet_ledger.ensure_period_and_trial(
        ws,
        policy,
        user_id=user_id,
        store=credit_store,
    )
    daily_used = credit_store.get_daily_usage(ws)
    low = False
    if wallet.available > 0:
        basis = max(
            policy.included_credits_monthly,
            policy.trial_credits,
            wallet.available,
            1,
        )
        low = wallet.available <= max(1, int(basis * 0.2))
    return {
        "workspace_id": ws,
        "policy": policy.to_dict(),
        "wallet": wallet.to_dict(),
        "daily_credits_used": daily_used,
        "daily_cap": policy.trial_daily_cap_credits or None,
        "low_credit": low,
        "exhausted": policy.managed_ai_available and wallet.available <= 0,
        "byok_available": True,
        "actions_when_exhausted": ["byok", "purchase_credits", "upgrade"],
    }


def _run_coro_sync(coro: Any) -> Any:
    """Run an async wallet helper from sync code when no loop is running."""
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Already inside an event loop; skip sync gate (async path handles it).
    return None


def sync_assert_managed_call_allowed(**kwargs: Any) -> WalletCheckResult | None:
    return _run_coro_sync(assert_managed_call_allowed(**kwargs))


def sync_debit_managed_call(**kwargs: Any) -> WalletDebitResult | None:
    return _run_coro_sync(debit_managed_call(**kwargs))


def usage_tokens_from_response(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0
    if isinstance(usage, dict):
        return (
            int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0),
            int(usage.get("output_tokens") or usage.get("completion_tokens") or 0),
        )
    return (
        int(
            getattr(usage, "input_tokens", 0)
            or getattr(usage, "prompt_tokens", 0)
            or 0
        ),
        int(
            getattr(usage, "output_tokens", 0)
            or getattr(usage, "completion_tokens", 0)
            or 0
        ),
    )


def estimate_message_tokens(messages: list | None) -> int:
    total = 0
    for msg in messages or []:
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += len(str(part.get("text") or ""))
                else:
                    total += len(str(part))
        else:
            total += len(str(content or ""))
    return max(1, total // 4)
