"""Policy compliance checks for security operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def compliance_status() -> dict[str, Any]:
    from keprix.integrations.product_registry import list_registered_products
    from keprix.security.product_policy import list_policies
    from keprix.security.scout_registration import ScoutRegistration

    agents = ScoutRegistration().list_local_registrations()
    policies = list_policies()
    registered = list_registered_products()
    rows: list[dict[str, Any]] = []
    for agent in agents:
        pid = str(agent.get("product_id") or "")
        policy = policies.get(pid)
        rows.append(
            {
                "product_id": pid,
                "registered": True,
                "has_policy": policy is not None,
                "security_profile": (policy or {}).get("security_profile")
                or agent.get("security_profile")
                or "standard",
                "compliant": policy is not None or pid == "keprix",
            }
        )
    for row in registered:
        pid = str(row.get("product_id") or "")
        if any(item["product_id"] == pid for item in rows):
            continue
        rows.append(
            {
                "product_id": pid,
                "registered": True,
                "has_policy": pid in policies,
                "security_profile": row.get("security_policy") or "standard",
                "compliant": pid in policies,
            }
        )
    compliant = all(item["compliant"] for item in rows) if rows else True
    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ok": compliant,
        "products": rows,
    }


def compliance_sync(*, full: bool = False) -> dict[str, Any]:
    status = compliance_status()
    frameworks = ["SOC2", "GDPR"] if full else ["SOC2"]
    return {
        "synced_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "frameworks": frameworks,
        "products": status.get("products") or [],
        "ok": status.get("ok", False),
    }
