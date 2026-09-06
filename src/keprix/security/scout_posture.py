"""Deterministic local security posture scoring from existing Scout signals."""

from __future__ import annotations

from typing import Any


def _finding(severity: str, category: str, evidence: Any, action: str) -> dict[str, Any]:
    return {"severity": severity, "category": category, "evidence": evidence, "recommended_action": action, "status": "open"}


def compute_posture(signals: dict[str, Any] | None = None) -> dict[str, Any]:
    signals = signals or {}
    score = 100
    findings: list[dict[str, Any]] = []
    rules = (
        ("failed_logins", 5, "authentication", "Review failed login bursts"),
        ("tool_acl_denials", 4, "authorization", "Review denied tool access"),
        ("egress_anomalies", 8, "egress", "Inspect egress policy violations"),
        ("secret_scans", 10, "secrets", "Rotate and remove exposed secrets"),
        ("open_incidents", 12, "incidents", "Close or assign open incidents"),
    )
    for key, weight, category, action in rules:
        count = max(0, int(signals.get(key) or 0))
        score -= min(30, count * weight)
        if count:
            severity = "critical" if count * weight >= 20 else "warning"
            findings.append(_finding(severity, category, {"signal": key, "count": count}, action))
    score = max(0, min(100, score))
    grade = "strong" if score >= 90 else "good" if score >= 75 else "fair" if score >= 55 else "poor" if score >= 30 else "critical"
    return {"score": score, "grade": grade, "findings": findings, "signals": signals}


def current_posture() -> dict[str, Any]:
    from keprix.security.scout_metrics import product_metrics
    from keprix.security.scout_correlation import correlate_attacks

    metrics = product_metrics("keprix")
    correlated = correlate_attacks(limit=100)
    signals = {
        "tool_acl_denials": metrics.get("tool_acl_denials", 0),
        "egress_anomalies": metrics.get("egress_anomalies", 0),
        "failed_logins": metrics.get("failed_logins", 0),
        "secret_scans": metrics.get("secret_scans", 0),
        "open_incidents": len(correlated),
    }
    return compute_posture(signals)
