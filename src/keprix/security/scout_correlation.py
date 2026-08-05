"""Local cross-product signal correlation for the Scout dashboard."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix_cli.config import get_keprix_home


def _signal_log_path() -> Path:
    return get_keprix_home() / "scout" / "signal_log.jsonl"


def append_signal_event(event: dict[str, Any]) -> None:
    path = _signal_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def _read_recent_events(*, limit: int = 500) -> list[dict[str, Any]]:
    path = _signal_log_path()
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def correlate_attacks(*, limit: int = 20) -> list[dict[str, Any]]:
    """Group recent injection/tool abuse signals across products."""
    by_key: dict[str, dict[str, Any]] = {}
    for event in _read_recent_events():
        category = str(event.get("category") or "")
        if category not in {"prompt_injection", "tool_abuse", "egress_violation"}:
            continue
        action = str(event.get("action") or "")
        patterns = tuple(sorted((event.get("details") or {}).get("patterns_matched") or []))
        key = f"{category}:{action}:{patterns}"
        bucket = by_key.setdefault(
            key,
            {
                "type": "coordinated_attack" if category == "prompt_injection" else "anomalous_tool_usage",
                "category": category,
                "action": action,
                "products": defaultdict(int),
                "attempts": 0,
                "threat_score": 0.0,
                "pattern": list(patterns),
            },
        )
        product = str(event.get("product") or "keprix")
        bucket["products"][product] += 1
        bucket["attempts"] += 1
        bucket["threat_score"] = max(
            float(bucket.get("threat_score") or 0.0),
            float(event.get("threat_score") or 0.0),
        )

    results: list[dict[str, Any]] = []
    for item in by_key.values():
        products_hit = dict(item["products"])
        if len(products_hit) < 1:
            continue
        score = min(100.0, float(item["threat_score"]) * 100 + item["attempts"] * 2)
        results.append(
            {
                "type": item["type"],
                "category": item["category"],
                "action": item["action"],
                "products_hit": products_hit,
                "attempts": item["attempts"],
                "threat_score": int(score),
                "pattern": item["pattern"],
                "recommended": _recommendation(item["type"], products_hit),
            }
        )
    results.sort(key=lambda row: row["threat_score"], reverse=True)
    return results[:limit]


def _recommendation(attack_type: str, products_hit: dict[str, int]) -> str:
    if attack_type == "coordinated_attack" and len(products_hit) > 1:
        return "Suspend affected sessions and review shared ingress IP ranges"
    if attack_type == "anomalous_tool_usage":
        return "Quarantine high-risk tools on affected products"
    return "Review recent signals in Scout dashboard"


def dashboard_summary() -> dict[str, Any]:
    from keprix.security.scout_metrics import product_metrics
    from keprix.security.scout_registration import ScoutRegistration

    agents = ScoutRegistration().list_local_registrations()
    metrics = product_metrics()
    rows = []
    for agent in agents:
        pid = agent.get("product_id")
        m = metrics.get(pid or "", {})
        rows.append(
            {
                "product_id": pid,
                "product_name": agent.get("product_name"),
                "version": agent.get("product_version"),
                "security_profile": agent.get("security_profile", "standard").upper(),
                "status": str(agent.get("status") or "online").upper(),
                "signals_24h": int(m.get("signals_24h") or 0),
                "alerts_warning": int(m.get("alerts_warning") or 0),
                "alerts_critical": int(m.get("alerts_critical") or 0),
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "agent_count": len(rows),
        "agents": rows,
        "correlated_attacks": len(correlate_attacks(limit=100)),
    }
