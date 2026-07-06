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
