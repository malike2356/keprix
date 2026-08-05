"""Server-side plan and deployment policy for managed AI credits.

Never trust plan or workspace IDs from request body or query.
Resolve edition and plan from env + subscription store only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from keprix.billing.config_loader import billing_enabled, load_billing_config
from keprix.licensing.edition import current_edition

DeploymentMode = Literal["community", "self_hosted", "hosted_trial", "starter", "pro"]
BillingMode = Literal["byok", "managed"]

# Default trial grant: 500 credits = $5 charged value at 1 credit = 1 cent.
DEFAULT_TRIAL_CREDITS = 500
DEFAULT_TRIAL_DAILY_CAP_CREDITS = 100
DEFAULT_INCLUDED_CREDITS_PRO = 1500
DEFAULT_INCLUDED_CREDITS_STARTER = 500


@dataclass(frozen=True)
class AiWalletPolicy:
    deployment_mode: DeploymentMode
    plan_id: str
    managed_ai_available: bool
    byok_default: bool
    included_credits_monthly: int
    trial_credits: int
    trial_daily_cap_credits: int
    platform_markup: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_mode": self.deployment_mode,
            "plan_id": self.plan_id,
            "managed_ai_available": self.managed_ai_available,
            "byok_default": self.byok_default,
            "included_credits_monthly": self.included_credits_monthly,
            "trial_credits": self.trial_credits,
            "trial_daily_cap_credits": self.trial_daily_cap_credits,
            "platform_markup": self.platform_markup,
        }


def is_hosted_deployment() -> bool:
    """True when this instance is Verlox-hosted SaaS (managed tokens available)."""
    raw = (os.environ.get("KEPRIX_HOSTED") or os.environ.get("KEPRIX_DEPLOYMENT") or "").strip().lower()
    if raw in {"1", "true", "yes", "hosted", "saas", "cloud"}:
        return True
    if raw in {"0", "false", "no", "self_hosted", "self-hosted", "community"}:
        return False
    # Billing enabled with Stripe on a non-community edition implies hosted SaaS.
    if billing_enabled() and (os.environ.get("KEPRIX_BILLING_PROVIDER") or "").strip().lower() == "stripe":
        return True
    return False


def _wallet_config() -> dict[str, Any]:
    cfg = load_billing_config()
    if cfg is None:
        return {}
    raw = getattr(cfg, "ai_wallet", None)
    if raw is None:
        return {}
    if hasattr(raw, "model_dump"):
        return dict(raw.model_dump())
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _plan_wallet_flags(plan_id: str) -> dict[str, Any]:
    cfg = load_billing_config()
    if cfg is None:
        return {}
    plan = cfg.plan_by_id(plan_id)
    if plan is None:
        return {}
    flags = dict(plan.feature_flags or {})
    return {
        "managed_ai": bool(flags.get("managed_ai", False)),
        "included_credits": int(flags.get("ai_included_credits") or 0),
        "trial_credits": int(flags.get("ai_trial_credits") or 0),
        "trial_daily_cap": int(flags.get("ai_trial_daily_cap_credits") or 0),
    }


async def resolve_plan_id(user_id: str | None) -> str:
    """Resolve the active billing plan for a user from the subscription store."""
    uid = (user_id or "").strip() or "default"
    if not billing_enabled():
        return "community"
    try:
        from keprix.billing.store import get_billing_store

        sub = await get_billing_store().get_subscription(uid)
        if sub and sub.get("plan_id"):
            return str(sub["plan_id"])
        status = str(sub.get("status") or "") if sub else ""
        if status == "trialing":
            return str(sub.get("plan_id") or "pro")
    except Exception:
        pass
    return "community"


async def resolve_policy(*, user_id: str | None = None, plan_id: str | None = None) -> AiWalletPolicy:
    """Build wallet policy from server-side state only.

    ``plan_id`` may be passed only when already resolved server-side (e.g. from
    the subscription store). Client-supplied plan IDs must not be passed here.
    """
    wallet_cfg = _wallet_config()
    markup = float(wallet_cfg.get("markup") or 2.0)
    trial_default = int(wallet_cfg.get("trial_credits") or DEFAULT_TRIAL_CREDITS)
    daily_default = int(wallet_cfg.get("trial_daily_cap_credits") or DEFAULT_TRIAL_DAILY_CAP_CREDITS)

    resolved_plan = plan_id or await resolve_plan_id(user_id)
    flags = _plan_wallet_flags(resolved_plan)
    hosted = is_hosted_deployment()
    edition = current_edition()

    if not hosted:
        mode: DeploymentMode = "community" if edition == "community" else "self_hosted"
        return AiWalletPolicy(
            deployment_mode=mode,
            plan_id=resolved_plan,
            managed_ai_available=False,
            byok_default=True,
            included_credits_monthly=0,
            trial_credits=0,
            trial_daily_cap_credits=0,
            platform_markup=markup,
        )

    # Hosted: map plan to deployment mode.
    if resolved_plan in {"community", "free"}:
        mode = "hosted_trial"
        managed = True
        included = int(flags.get("included_credits") or 0)
        trial = int(flags.get("trial_credits") or trial_default)
        daily = int(flags.get("trial_daily_cap") or daily_default)
    elif resolved_plan in {"starter", "pro"} and flags.get("managed_ai", True):
        mode = "pro" if resolved_plan == "pro" else "starter"
        managed = True
        included = int(
            flags.get("included_credits")
            or (DEFAULT_INCLUDED_CREDITS_PRO if mode == "pro" else DEFAULT_INCLUDED_CREDITS_STARTER)
        )
        trial = int(flags.get("trial_credits") or 0)
        daily = int(flags.get("trial_daily_cap") or 0)
    elif resolved_plan == "team":
        mode = "pro"
        managed = True
        included = int(flags.get("included_credits") or DEFAULT_INCLUDED_CREDITS_PRO * 3)
        trial = 0
        daily = 0
    else:
        # Unknown paid plan on hosted: allow managed with conservative included=0
        # so prepaid balance is required (never unbounded).
        mode = "starter"
        managed = bool(flags.get("managed_ai", True))
        included = int(flags.get("included_credits") or 0)
        trial = int(flags.get("trial_credits") or 0)
        daily = int(flags.get("trial_daily_cap") or 0)

    return AiWalletPolicy(
        deployment_mode=mode,
        plan_id=resolved_plan,
        managed_ai_available=managed,
        byok_default=not managed,
        included_credits_monthly=included,
        trial_credits=trial,
        trial_daily_cap_credits=daily,
        platform_markup=markup,
    )


def resolve_billing_mode(
    *,
    policy: AiWalletPolicy,
    user_supplied_api_key: bool = False,
    force_managed: bool | None = None,
) -> BillingMode:
    """Decide whether this call uses managed tokens or BYOK.

    BYOK wins when the operator/user supplies their own key, or when managed AI
    is not available on the deployment.
    """
    if force_managed is False or user_supplied_api_key:
        return "byok"
    if force_managed is True and policy.managed_ai_available:
        return "managed"
    if not policy.managed_ai_available:
        return "byok"
    # Hosted managed default when no user key is present.
    env_mode = (os.environ.get("KEPRIX_AI_BILLING_MODE") or "").strip().lower()
    if env_mode in {"byok", "bring_your_own", "byo"}:
        return "byok"
    if env_mode in {"managed", "platform"}:
        return "managed"
    return "managed" if policy.managed_ai_available else "byok"


def trusted_workspace_id(
    *,
    session_workspace_id: str | None = None,
    auth_workspace_id: str | None = None,
    fallback: str = "default",
) -> str:
    """Pick a workspace id from server-set context only.

    Never accept body/query workspace_id for plan or wallet enforcement.
    """
    for candidate in (auth_workspace_id, session_workspace_id):
        value = (candidate or "").strip()
        if value:
            return value
    return fallback
