"""HTTP routes for feature health audit and build gate."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from keprix.auth.dependencies import get_current_user
from keprix.feature_health import (
    check_all_features,
    evaluate_build_gate,
    get_registry,
    seed_keprix_features,
    traffic_light,
)

router = APIRouter(prefix="/api/feature-health", tags=["feature-health"])


def _ensure_seeded() -> None:
    reg = get_registry()
    if not reg.get_all():
        seed_keprix_features(reg)


@router.get("")
async def feature_health_report(
    base_url: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    _ensure_seeded()
    report = check_all_features(base_url=base_url or "")
    gate = evaluate_build_gate()
    features = []
    for row in report["results"]:
        feat = row["feature"]
        features.append(
            {
                "name": feat.name,
                "status": row["status"],
                "trafficLight": traffic_light(row["status"]),
                "activeUsers7d": feat.health.active_users_7d,
                "errorRate7d": feat.health.error_rate_7d,
                "adoptionRate": feat.health.adoption_rate,
                "owner": feat.owner,
                "criticalPath": feat.critical_path,
                "lastTested": feat.health.last_tested,
                "smokes": row["smokes"],
            }
        )
    return {
        "ok": True,
        "checkedAt": report["checked_at"],
        "summary": report["summary"],
        "features": features,
        "gate": {
            "canBuildNewFeature": gate["allowed"],
            "blocked": gate["blocked"],
            "reason": gate["reason"],
            "blockingIssues": gate["blocking_issues"],
            "fixQueue": gate["fix_queue"],
            "deprecate": gate["deprecate"],
        },
    }


@router.get("/build-gate")
async def feature_health_build_gate(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _ensure_seeded()
    check_all_features(base_url="")
    gate = evaluate_build_gate()
    return {"ok": True, "canBuildNewFeature": gate["allowed"], **gate}
