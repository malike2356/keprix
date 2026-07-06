"""jamovi bridge HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from keprix.analytics.jamovi.analysis_plan import build_analysis_plan
from keprix.analytics.jamovi.export_bridge import prepare_export_package
from keprix.analytics.jamovi.module_catalog import list_modules
from keprix.analytics.jamovi.r_syntax import plan_to_r_script, store_user_r_syntax
from keprix.api.auth import require_api_auth

router = APIRouter(prefix="/api/analytics/jamovi", tags=["analytics-jamovi"])


class ExportBody(BaseModel):
    rows: list[dict[str, Any]] = Field(..., min_length=1)
    columns: list[dict[str, Any]] | None = None
    dataset_name: str = "dataset"
    suggested_analyses: list[str] | None = None


class PlanBody(BaseModel):
    dataset_name: str = "dataset"
    variables: list[str] = Field(..., min_length=1)
    analysis: str = "descriptives"


class RSyntaxBody(BaseModel):
    source: str = Field(..., min_length=1)
    analysis_id: str = "analysis-1"


@router.get("/modules")
async def modules(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"modules": list_modules()}


@router.post("/export")
async def export_package(body: ExportBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    try:
        package = prepare_export_package(
            body.rows,
            columns=body.columns,
            dataset_name=body.dataset_name,
            suggested_analyses=body.suggested_analyses,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "dataset_name": package["dataset_name"],
        "metadata": package["metadata"],
        "suggested_analyses": package["suggested_analyses"],
        "instructions": package["instructions"],
        "download_url": "/api/analytics/jamovi/export/download",
        "package_filename": package["package_filename"],
        "package_size_bytes": len(package["package_bytes"]),
        "_package_token": package["package_filename"],
    }


@router.post("/export/download")
async def download_package(body: ExportBody, _user: str = Depends(require_api_auth)) -> Response:
    package = prepare_export_package(
        body.rows,
        columns=body.columns,
        dataset_name=body.dataset_name,
        suggested_analyses=body.suggested_analyses,
    )
    return Response(
        content=package["package_bytes"],
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{package["package_filename"]}"'},
    )


@router.post("/plan")
async def analysis_plan(body: PlanBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    plan = build_analysis_plan(
        dataset_name=body.dataset_name,
        variables=body.variables,
        analysis=body.analysis,
    )
    return {"plan": plan, "r_script": plan_to_r_script(plan)}


@router.post("/r-syntax")
async def capture_r_syntax(body: RSyntaxBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"artifact": store_user_r_syntax(body.source, analysis_id=body.analysis_id)}
