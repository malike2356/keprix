"""Security operations reports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def report_24h() -> dict[str, Any]:
    from keprix.security.scout_correlation import correlate_attacks, dashboard_summary
    from keprix.security.scout_metrics import product_metrics
    from keprix.incident.store import list_incidents

    summary = dashboard_summary()
    metrics = product_metrics()
    total_signals = sum(int(row.get("signals_24h") or 0) for row in metrics.values())
    return {
        "period": "24h",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "agents": summary.get("agents") or [],
        "signals_24h": total_signals,
        "correlated_attacks": correlate_attacks(limit=10),
        "open_incidents": list_incidents(),
    }


def report_weekly() -> dict[str, Any]:
    base = report_24h()
    from keprix.security.product_policy import list_policies, policy_history
    from keprix.forensics.snapshot import list_snapshots

    base["period"] = "weekly"
    base["policy_count"] = len(list_policies())
    base["policy_changes"] = policy_history(limit=50)
    base["forensic_snapshots"] = list_snapshots()[:20]
    return base
