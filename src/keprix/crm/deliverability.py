"""Deliverability rates and Soft Wall gate helpers (honest zeros when no events)."""

from __future__ import annotations

from typing import Any

from keprix.email.deliverability_auth import POLICY

# Aligned with shared/email/policy.json (complaint 0.1%, bounce 2%).
DEFAULT_THRESHOLDS = {
    "bounce_rate_pct": float((POLICY.get("thresholds") or {}).get("bounceRateMaxPct", 2.0)),
    "complaint_rate_pct": float(
        (POLICY.get("thresholds") or {}).get("spamComplaintRateMaxPct", 0.1)
    ),
    "unsubscribe_rate_pct": 2.0,
    "inbox_rate_min_pct": float((POLICY.get("thresholds") or {}).get("inboxRateMinPct", 99.0)),
}


def compute_deliverability_snapshot(store: Any, workspace_id: str) -> dict[str, Any]:
    """Aggregate sender readiness, kill switches, and period rates.

    Rates use suppression sources and outbox outcomes. Missing signal => 0.0,
    never fake demo traffic.
    """
    readiness = store.list_sender_readiness(workspace_id)
    switches = store.list_kill_switches(workspace_id)
    suppressions = store.list_suppressions(workspace_id)
    outbox = store.list_outbox(workspace_id, limit=5000)

    sent_like = [
        o
        for o in outbox
        if str(o.get("status") or "").lower() in {"sent", "delivered", "failed", "dead_letter", "pending"}
    ]
    sent_count = len(
        [o for o in outbox if str(o.get("status") or "").lower() in {"sent", "delivered"}]
    )
    denom = max(sent_count, len(sent_like), 0)

    bounce_n = sum(
        1
        for s in suppressions
        if "bounce" in str(s.get("reason") or "").lower()
        or "bounce" in str(s.get("source") or "").lower()
    )
    complaint_n = sum(
        1
        for s in suppressions
        if "complaint" in str(s.get("reason") or "").lower()
        or "complaint" in str(s.get("source") or "").lower()
        or "spam" in str(s.get("reason") or "").lower()
    )
    unsub_n = sum(
        1
        for s in suppressions
        if "unsub" in str(s.get("reason") or "").lower()
        or "unsub" in str(s.get("source") or "").lower()
    )

    def pct(n: int) -> float:
        if denom <= 0:
            return 0.0
        return round((100.0 * n) / denom, 3)

    rates = {
        "period": "all_time",
        "sent_count": sent_count,
        "outbox_count": len(outbox),
        "bounce_count": bounce_n,
        "complaint_count": complaint_n,
        "unsubscribe_count": unsub_n,
        "bounce_rate_pct": pct(bounce_n),
        "complaint_rate_pct": pct(complaint_n),
        "unsubscribe_rate_pct": pct(unsub_n),
        "inbox_rate_proxy_pct": (
            round((100.0 * sent_count) / max(sent_count + bounce_n + complaint_n, 1), 1)
            if sent_count or bounce_n or complaint_n
            else None
        ),
        "note": (
            "Rates are 0 when no sends or no matching suppressions exist (honest empty). "
            "inbox_rate_proxy_pct is not Postmaster placement; label as proxy."
        ),
    }

    breaches: list[str] = []
    if rates["bounce_rate_pct"] > DEFAULT_THRESHOLDS["bounce_rate_pct"]:
        breaches.append(
            f"bounce_rate_pct {rates['bounce_rate_pct']} exceeds "
            f"{DEFAULT_THRESHOLDS['bounce_rate_pct']}"
        )
    if rates["complaint_rate_pct"] > DEFAULT_THRESHOLDS["complaint_rate_pct"]:
        breaches.append(
            f"complaint_rate_pct {rates['complaint_rate_pct']} exceeds "
            f"{DEFAULT_THRESHOLDS['complaint_rate_pct']}"
        )
    if rates["unsubscribe_rate_pct"] > DEFAULT_THRESHOLDS["unsubscribe_rate_pct"]:
        breaches.append(
            f"unsubscribe_rate_pct {rates['unsubscribe_rate_pct']} exceeds "
            f"{DEFAULT_THRESHOLDS['unsubscribe_rate_pct']}"
        )
    if (
        rates["inbox_rate_proxy_pct"] is not None
        and rates["inbox_rate_proxy_pct"] < DEFAULT_THRESHOLDS["inbox_rate_min_pct"]
        and (sent_count + bounce_n + complaint_n) >= 20
    ):
        breaches.append(
            f"inbox_rate_proxy_pct {rates['inbox_rate_proxy_pct']} below "
            f"{DEFAULT_THRESHOLDS['inbox_rate_min_pct']}"
        )

    workspace_killed = any(
        sw.get("enabled") and str(sw.get("scope") or "") == "workspace" for sw in switches
    )

    domains_verified = sum(1 for r in readiness if r.get("verified"))
    checklist = {
        "has_sender_domain": len(readiness) > 0,
        "any_domain_verified": domains_verified > 0,
        "spf_ok_any": any(r.get("spf_ok") for r in readiness),
        "dkim_ok_any": any(r.get("dkim_ok") for r in readiness),
        "dmarc_ok_any": any(r.get("dmarc_ok") for r in readiness),
        "workspace_kill_switch_off": not workspace_killed,
        "rates_within_policy": len(breaches) == 0,
        "transactional_marketing_separated": _domains_separated(readiness),
    }

    soft_wall_block = len(breaches) > 0 or workspace_killed or not checklist["has_sender_domain"]

    return {
        "sender_readiness": readiness,
        "kill_switches": switches,
        "rates": rates,
        "thresholds": dict(DEFAULT_THRESHOLDS),
        "policy_version": POLICY.get("version"),
        "dmarc_ladder": list(POLICY.get("dmarcLadder") or ["none", "quarantine", "reject"]),
        "breaches": breaches,
        "checklist": checklist,
        "soft_wall_block_cold_send": soft_wall_block,
        "soft_wall_block_reason": (
            "; ".join(breaches)
            if breaches
            else (
                "workspace kill switch enabled"
                if workspace_killed
                else (
                    "no sender domain configured"
                    if not checklist["has_sender_domain"]
                    else None
                )
            )
        ),
    }


def _domains_separated(readiness: list[dict[str, Any]]) -> bool:
    """True when at least two distinct sender domains exist, or roles are tagged."""
    domains = {str(r.get("domain") or "").lower() for r in readiness if r.get("domain")}
    if len(domains) >= 2:
        return True
    roles = {str(r.get("role") or r.get("purpose") or "").lower() for r in readiness}
    return "transactional" in roles and "marketing" in roles
