"""Feature gate matrix built from billing.yaml plans."""

from __future__ import annotations

from typing import Any

from keprix.billing.config_loader import load_billing_config


def build_feature_matrix() -> dict[str, dict[str, Any]]:
    cfg = load_billing_config()
    if cfg is None:
        return {}
    return {plan.id: dict(plan.feature_flags) for plan in cfg.plans}


def plan_ids() -> list[str]:
    cfg = load_billing_config()
    if cfg is None:
        return []
    return [plan.id for plan in cfg.plans]
