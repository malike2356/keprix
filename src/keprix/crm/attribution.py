"""Deal attribution modes and Nice-wave reporting (prompt 465)."""

from __future__ import annotations

from typing import Any

from keprix.crm.nice_schema import ensure_nice_schema

ATTRIBUTION_MODES = frozenset({"sourced", "influenced", "closed"})


def set_deal_attribution(
    store: Any,
    workspace_id: str,
    deal_id: str,
    *,
    mode: str,
    notes: str | None = None,
    stripe_customer_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    mode = (mode or "").strip().lower()
    if mode not in ATTRIBUTION_MODES:
        return {"ok": False, "error": "invalid_mode", "allowed": sorted(ATTRIBUTION_MODES)}
    deal = store.get_deal(ws, deal_id)
    if not deal:
        return {"ok": False, "error": "not_found"}
    fields: dict[str, Any] = {"attribution_mode": mode, "attribution_notes": notes}
    # Stripe customer id is read-only link; never create prices.
    if stripe_customer_id is not None:
        fields["stripe_customer_id"] = stripe_customer_id
    ensure_nice_schema(store)
    with store._lock:
        store._conn.execute(
            """
            UPDATE crm_deals
            SET attribution_mode = ?, attribution_notes = ?,
                stripe_customer_id = COALESCE(?, stripe_customer_id),
                updated_at = datetime('now')
            WHERE workspace_id = ? AND id = ?
            """,
            (mode, notes, stripe_customer_id, ws, deal_id),
        )
        store._conn.commit()
    updated = store.get_deal(ws, deal_id)
    return {"ok": True, "deal": updated}


def attribution_report(store: Any, workspace_id: str) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    deals = store.list_deals(ws, limit=2000)
    by_mode: dict[str, list[dict[str, Any]]] = {"sourced": [], "influenced": [], "closed": [], "unset": []}
    vanity_excluded = 0
    for deal in deals:
        mode = str(deal.get("attribution_mode") or "").lower()
        # Vanity sends alone are insufficient for closed success.
        tags = [str(t).lower() for t in (deal.get("tags") or [])]
        if mode == "closed" and "vanity_sends_only" in tags:
            vanity_excluded += 1
            continue
        if mode in by_mode:
            by_mode[mode].append(deal)
        else:
            by_mode["unset"].append(deal)

    def _sum(rows: list[dict[str, Any]]) -> float:
        return float(sum(float(r.get("amount") or 0) for r in rows))

    # Cost per qualified opportunity from enrich/send style scores when present.
    enrich_cost = 0.0
    send_cost = 0.0
    for lead in store.list_leads(ws, limit=2000):
        scores = lead.get("scores") or {}
        if isinstance(scores, dict):
            enrich_cost += float(scores.get("enrich_cost") or 0)
            send_cost += float(scores.get("send_cost") or 0)
    qualified = [d for d in deals if str(d.get("stage") or "") in {"qualified", "booked", "customer", "paying"}]
    denom = max(1, len(qualified))
    return {
        "by_mode": {k: {"count": len(v), "amount": _sum(v), "deals": v[:50]} for k, v in by_mode.items()},
        "vanity_excluded": vanity_excluded,
        "cost_per_qualified_opportunity": round((enrich_cost + send_cost) / denom, 4),
        "costs": {"enrich": enrich_cost, "send": send_cost},
        "note": "Stripe customer ids are linked read-only. No Stripe prices are created.",
    }


def assignment_rules_check(mode: str, *, has_touch: bool, is_closed_won: bool, vanity_only: bool) -> str:
    """Deterministic attribution assignment helper for tests."""
    if vanity_only and is_closed_won:
        return "reject_vanity"
    if is_closed_won:
        return "closed"
    if has_touch and mode == "influenced":
        return "influenced"
    return "sourced"
