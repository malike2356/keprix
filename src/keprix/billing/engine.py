"""Billing engine bootstrap."""

from __future__ import annotations

import logging
from typing import Any

from keprix.billing.config_loader import billing_enabled, load_billing_config
from keprix.billing.store import ensure_billing_tables
from keprix.billing.stripe.products import sync_products_and_prices

logger = logging.getLogger(__name__)


async def bootstrap_billing() -> dict[str, Any]:
    cfg = load_billing_config()
    if cfg is None:
        logger.info("No billing config found; all features unrestricted")
        return {"enabled": False, "reason": "no billing.yaml"}

    if not billing_enabled():
        logger.info("Billing config present but provider not enabled")
        return {"enabled": False, "reason": "provider not configured", "product_id": cfg.product.id}

    await ensure_billing_tables()
    sync_result = await sync_products_and_prices(cfg)
    _register_plan_quotas(cfg)
    logger.info(
        "Billing engine ready for %s: %s plans, %s addons",
        cfg.product.name,
        len(cfg.plans),
        len(cfg.addons),
    )
    return {
        "enabled": True,
        "product_id": cfg.product.id,
        "product_name": cfg.product.name,
        "plans": len(cfg.plans),
        "addons": len(cfg.addons),
        "stripe_sync": sync_result,
    }


def _register_plan_quotas(cfg: Any) -> None:
    """Register product token quotas so /admin/quotas has real limits."""
    try:
        from keprix.quotas.quota_config import ProductQuota, ResourceType, get_quota_config
    except Exception:
        return

    # Use the highest paid plan caps as the product default ceiling for CE instances.
    tokens_in = 500_000
    tokens_out = 500_000
    for plan in cfg.plans:
        flags = dict(plan.feature_flags or {})
        try:
            tokens_in = max(tokens_in, int(flags.get("llm_tokens_in") or 0))
            tokens_out = max(tokens_out, int(flags.get("llm_tokens_out") or 0))
        except (TypeError, ValueError):
            continue

    get_quota_config().register(
        ProductQuota(
            product_id=cfg.product.id,
            period="monthly",
            limits={
                ResourceType.LLM_TOKENS_IN: tokens_in,
                ResourceType.LLM_TOKENS_OUT: tokens_out,
                ResourceType.TOOL_CALLS: 100_000,
                ResourceType.STORAGE_BYTES: 10_000_000_000,
                ResourceType.VOICE_MINUTES: 1_000,
                ResourceType.API_CALLS: 100_000,
                ResourceType.MUTATION_RUNS: 5_000,
                ResourceType.ESTIMATED_TOKENS: tokens_in + tokens_out,
            },
        )
    )
