"""Admin API for Hermes upstream adoption review queue.

Endpoints:
  GET  /api/admin/upstream                 - report + pending/all features
  GET  /api/admin/upstream/features        - list features
  POST /api/admin/upstream/check           - run upstream check
  POST /api/admin/upstream/features/{id}/decide
  POST /api/admin/upstream/features/{id}/adopt
  POST /api/admin/upstream/features/{id}/complete
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.upstream.hermes_adoption import AdoptionPromptGenerator
from keprix.upstream.hermes_monitor import HermesMonitor

router = APIRouter(prefix="/api/admin/upstream", tags=["admin", "upstream"])


def _monitor() -> HermesMonitor:
    return HermesMonitor()


@router.get("")
async def get_upstream_overview(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    monitor = _monitor()
    report = monitor.report()
    pending = [f.to_dict() for f in monitor.list_features(pending_only=True)]
    return {
        "report": report,
        "pending": pending,
        "pending_count": len(pending),
    }


@router.get("/features")
async def list_upstream_features(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    pending: bool = Query(default=False),
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    monitor = _monitor()
    features = monitor.list_features(category=category, status=status, pending_only=pending)
    return {"features": [f.to_dict() for f in features], "count": len(features)}


@router.post("/check")
async def run_upstream_check(
    enrichment: bool = Query(default=True),
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    monitor = _monitor()
    features = await monitor.check(fetch_enrichment=enrichment)
    return {
        "new_features": [f.to_dict() for f in features],
        "count": len(features),
        "report": monitor.report(),
    }


class DecideBody(BaseModel):
    status: str = Field(..., description="adopt | adopt_with_hardening | skip | defer | blocked | already_have")
    notes: str = ""
    equivalent: str | None = None
    decided_by: str = "admin"


@router.post("/features/{feature_id}/decide")
async def decide_feature(
    feature_id: str,
    body: DecideBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    monitor = _monitor()
    try:
        feature = monitor.decide(
            feature_id,
            body.status,
            decided_by=body.decided_by or "admin",
            notes=body.notes,
            keprix_equivalent=body.equivalent,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"feature": feature.to_dict()}


@router.post("/features/{feature_id}/adopt")
async def adopt_feature(
    feature_id: str,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    monitor = _monitor()
    generator = AdoptionPromptGenerator(monitor)
    try:
        prompt_path = generator.generate(feature_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    feature = monitor.get_feature(feature_id)
    return {
        "prompt_path": str(prompt_path),
        "work_package_path": feature.work_package_path if feature else None,
        "feature": feature.to_dict() if feature else None,
    }


class CompleteBody(BaseModel):
    equivalent: str
    notes: str = ""
    decided_by: str = "admin"


@router.post("/features/{feature_id}/complete")
async def complete_feature(
    feature_id: str,
    body: CompleteBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    monitor = _monitor()
    try:
        feature = monitor.mark_complete(
            feature_id,
            keprix_equivalent=body.equivalent,
            notes=body.notes,
            decided_by=body.decided_by or "admin",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"feature": feature.to_dict()}
