"""Managed AI credit wallet for hosted Keprix.

Community and self-hosted deployments stay BYOK-first.
Hosted trial and paid plans meter managed tokens through an immutable ledger.
"""

from keprix.billing.wallet.enforcer import (
    ManagedAiExhausted,
    WalletCheckResult,
    WalletDebitResult,
    assert_managed_call_allowed,
    check_managed_call,
    debit_managed_call,
    wallet_status,
)
from keprix.billing.wallet.policy import (
    AiWalletPolicy,
    is_hosted_deployment,
    resolve_billing_mode,
    resolve_plan_id,
    resolve_policy,
    trusted_workspace_id,
)
from keprix.billing.wallet.pricing import credits_for_usage, estimate_credits_for_tokens, pricing_for
from keprix.billing.wallet.store import AiCreditStore, get_ai_credit_store, reset_ai_credit_store_for_tests

__all__ = [
    "AiCreditStore",
    "AiWalletPolicy",
    "ManagedAiExhausted",
    "WalletCheckResult",
    "WalletDebitResult",
    "assert_managed_call_allowed",
    "check_managed_call",
    "credits_for_usage",
    "debit_managed_call",
    "estimate_credits_for_tokens",
    "get_ai_credit_store",
    "is_hosted_deployment",
    "pricing_for",
    "reset_ai_credit_store_for_tests",
    "resolve_billing_mode",
    "resolve_plan_id",
    "resolve_policy",
    "trusted_workspace_id",
    "wallet_status",
]
