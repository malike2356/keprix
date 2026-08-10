"""Simulate an AI agent filtering productSpec.json against buy criteria."""

from __future__ import annotations

from typing import Any

from keprix.product_discovery.spec import build_product_spec


def evaluate_buy_decision(
    criteria: dict[str, Any],
    *,
    spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return matching tiers and a buy/no-buy decision from structured fields only.

    Example criteria::

        {
          "maxMonthlyAmountMajor": 50,
          "currency": "GBP",
          "requireSso": True,
          "requireCompliance": ["GDPR"],
          "requireApiAccess": False,
        }
    """
    spec = spec or build_product_spec()
    currency = str(criteria.get("currency") or "GBP").upper()
    max_monthly = criteria.get("maxMonthlyAmountMajor")
    require_sso = bool(criteria.get("requireSso"))
    require_api = bool(criteria.get("requireApiAccess"))
    require_compliance = [str(c) for c in (criteria.get("requireCompliance") or [])]

    compliance = {str(c) for c in (spec.get("compliance") or [])}
    missing_compliance = [c for c in require_compliance if c not in compliance]

    sso = spec.get("sso") or {}
    sso_addon_major = float(sso.get("addonAmountMajor") or 0)
    sso_available = bool(sso.get("available"))

    matches: list[dict[str, Any]] = []
    for tier in spec.get("pricingTiers") or []:
        if str(tier.get("currency") or "").upper() != currency:
            continue
        interval = tier.get("interval")
        if interval not in {None, "month"}:
            continue
        amount = float(tier.get("amountMajor") or 0)
        effective = amount
        has_sso = bool(tier.get("sso"))
        if require_sso and not has_sso:
            if not sso_available:
                continue
            # SSO is a Team addon; only Team can attach it.
            if "team" not in str(tier.get("id") or ""):
                continue
            effective = amount + sso_addon_major
            has_sso = True
        if max_monthly is not None and effective > float(max_monthly):
            continue
        if require_api and not tier.get("apiAccess"):
            continue
        matches.append(
            {
                "tierId": tier.get("id"),
                "name": tier.get("name"),
                "amountMajor": amount,
                "effectiveMonthlyMajor": effective,
                "currency": currency,
                "sso": has_sso,
                "apiAccess": bool(tier.get("apiAccess")),
            }
        )

    buy = bool(matches) and not missing_compliance
    reason_parts: list[str] = []
    if missing_compliance:
        reason_parts.append(f"missing compliance: {', '.join(missing_compliance)}")
    if not matches:
        reason_parts.append("no pricing tier matched numeric filters")
    if buy:
        reason_parts.append(f"matched {len(matches)} tier(s)")

    return {
        "buy": buy,
        "matches": matches,
        "recommended": matches[0] if matches else None,
        "criteria": criteria,
        "product": spec.get("name"),
        "reason": "; ".join(reason_parts),
    }
