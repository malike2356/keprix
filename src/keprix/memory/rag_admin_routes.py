"""RAG admin facade over the real rag_pipeline registry (no in-memory theatre)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/rag-admin", tags=["rag-admin"])

DEFAULT_PIPELINE_ID = os.getenv("KEPRIX_RAG_DEFAULT_PIPELINE_ID", "production-default")


class IngestBody(BaseModel):
    pipeline_id: str = DEFAULT_PIPELINE_ID
    content: str = Field(default="", min_length=0)
    source_id: str = "rag-admin-trigger"
    store_kind: str = "memory"


@router.get("/pipelines")
async def list_pipelines(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    from keprix.rag_pipeline.pipeline import get_pipeline_registry

    registry = get_pipeline_registry()
    known = list(getattr(registry, "_pipelines", {}).keys()) if hasattr(registry, "_pipelines") else []
    if DEFAULT_PIPELINE_ID not in known:
        known = [DEFAULT_PIPELINE_ID, *known]
    pipelines = []
    for pid in known:
        runs = registry.list_runs(pipeline_id=pid, limit=1)
        last = runs[0].to_dict() if runs else None
        pipelines.append(
            {
                "id": pid,
                "name": pid,
                "status": "idle" if not last else "ready",
                "last_run_at": (last or {}).get("finished_at") or (last or {}).get("started_at"),
                "run_count": len(registry.list_runs(pipeline_id=pid, limit=500)),
            }
        )
    last_eval: dict[str, Any]
    try:
        from keprix.rag_pipeline.deployment import assess_deployment

        report = assess_deployment(pipeline_id=DEFAULT_PIPELINE_ID, evaluations=[])
        if hasattr(report, "to_dict"):
            last_eval = report.to_dict()
        elif isinstance(report, dict):
            last_eval = report
        else:
            last_eval = {"report": str(report)}
    except Exception as exc:
        last_eval = {"status": "unavailable", "detail": str(exc)}
    return {
        "pipelines": pipelines,
        "last_eval": last_eval,
        "ui": "/data?tab=rag",
        "training": {
            "supported": False,
            "status": "unsupported",
            "detail": "No first-party model training job in CE. Use rag-pipeline ingest + eval instead.",
        },
    }


@router.post("/ingest")
async def trigger_ingest(body: IngestBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    from keprix.rag_pipeline.pipeline import get_pipeline_registry

    content = (body.content or "").strip()
    if not content:
        content = (
            f"# RAG admin health ping\n\n"
            f"Triggered at {datetime.now(timezone.utc).isoformat()} by "
            f"{admin.get('id') or admin.get('username') or 'admin'}."
        )
    registry = get_pipeline_registry()
    pipeline = registry.get_or_create(body.pipeline_id, store_kind=body.store_kind)
    user_id = str(admin.get("id") or admin.get("username") or "admin")
    result = await pipeline.ingest(
        user_id=user_id,
        source_type="plaintext",
        source_id=body.source_id,
        content=content,
    )
    return {"ok": True, "pipeline_id": body.pipeline_id, "result": result.to_dict()}
