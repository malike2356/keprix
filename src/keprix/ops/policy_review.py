"""Policy effectiveness review."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def policy_review() -> dict[str, Any]:
    from keprix.security.product_policy import list_policies, policy_history
    from keprix.security.scout_metrics import product_metrics

    policies = list_policies()
    metrics = product_metrics()
    recommendations: list[str] = []
    rows: list[dict[str, Any]] = []

    for product_id, policy in policies.items():
        m = metrics.get(product_id, {})
        signals = int(m.get("signals_24h") or 0)
        warnings = int(m.get("alerts_warning") or 0)
        critical = int(m.get("alerts_critical") or 0)
        row = {
            "product_id": product_id,
            "security_profile": policy.get("security_profile"),
            "version": policy.get("version"),
            "signals_24h": signals,
            "alerts_warning": warnings,
            "alerts_critical": critical,
        }
        if critical >= 3 and policy.get("security_profile") != "maximum":
            recommendations.append(f"Raise {product_id} to maximum security profile")
        if signals == 0 and policy.get("security_profile") == "maximum":
            recommendations.append(f"Review whether {product_id} still needs maximum profile")
        rows.append(row)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "policies": rows,
        "recent_changes": policy_history(limit=10),
        "recommendations": recommendations or ["No policy changes recommended"],
    }
