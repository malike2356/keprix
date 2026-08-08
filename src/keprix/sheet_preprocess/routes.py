"""HTTP API for spreadsheet preprocess under /api/crm/sheets (Soft Wall apply)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel

from keprix.auth.dependencies import get_current_user
from keprix.crm.roles import require_cap
from keprix.crm.soft_wall import gate_or_approve
from keprix.sheet_preprocess import email_ingest
from keprix.sheet_preprocess import service as sheet_service

router = APIRouter(prefix="/api/crm/sheets", tags=["crm-sheets"])
# Optional alias mounted by server.
alias_router = APIRouter(prefix="/api/sheet-preprocess", tags=["sheet-preprocess"])


def _uid(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _workspace(
    workspace_id: str | None,
    x_workspace_id: str | None,
    user: dict[str, Any],
) -> str:
    return (workspace_id or x_workspace_id or _uid(user) or "default").strip() or "default"


def _corr(request: Request) -> str:
    return request.headers.get("X-Correlation-Id") or str(uuid.uuid4())


class ProposeBody(BaseModel):
    upload_id: str | None = None
    source_path: str | None = None
    user_schema: dict[str, Any] | None = None
    metrics: list[str] | None = None
    context: str = ""
    domain_pack: str = "generic"
    sheet_name: str | int | None = None
    header_row: int = 0
    build_crm_plan: bool = True


class ApplyBody(BaseModel):
    approval_id: str | None = None
    force: bool = False
    upsert_crm: bool = True


def _register_routes(r: APIRouter) -> None:
    @r.post("/upload", status_code=201)
    async def upload_sheet(
        request: Request,
        file: UploadFile = File(...),
        workspace_id: str | None = Query(default=None),
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        require_cap(user, "edit")
        ws = _workspace(workspace_id, x_workspace_id, user)
        content = await file.read()
        try:
            meta = sheet_service.save_upload(
                ws,
                filename=file.filename or "upload.csv",
                content=content,
                actor_type="user",
                actor_id=_uid(user),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={"error_code": "upload_rejected", "message": str(exc)},
            ) from exc
        return {"upload": meta, "correlation_id": _corr(request)}

    @r.post("/propose", status_code=201)
    async def propose_sheet(
        body: ProposeBody,
        request: Request,
        workspace_id: str | None = Query(default=None),
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        require_cap(user, "edit")
        ws = _workspace(workspace_id, x_workspace_id, user)
        try:
            job = sheet_service.propose_sheet(
                ws,
                upload_id=body.upload_id,
                source_path=body.source_path,
                user_schema=body.user_schema,
                metrics=body.metrics,
                context=body.context,
                domain_pack=body.domain_pack,
                sheet_name=body.sheet_name,
                header_row=body.header_row,
                build_crm_plan=body.build_crm_plan,
                actor_type="user",
                actor_id=_uid(user),
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail={"error_code": str(exc) or "not_found"}
            ) from exc
        except PermissionError as exc:
            raise HTTPException(
                status_code=403, detail={"error_code": "path_outside_workspace"}
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail={"error_code": "propose_failed", "message": str(exc)}
            ) from exc
        return {"enrichment_job": job, "correlation_id": _corr(request)}

    @r.get("")
    async def list_sheet_jobs(
        workspace_id: str | None = Query(default=None),
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        require_cap(user, "view")
        ws = _workspace(workspace_id, x_workspace_id, user)
        items = sheet_service.list_jobs(ws)
        return {"items": items, "count": len(items)}

    @r.get("/email-ingest/status")
    async def email_ingest_status(
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        require_cap(user, "view")
        return email_ingest.status()

    @r.get("/{job_id}")
    async def get_sheet_job(
        job_id: str,
        workspace_id: str | None = Query(default=None),
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        require_cap(user, "view")
        ws = _workspace(workspace_id, x_workspace_id, user)
        job = sheet_service.get_job(ws, job_id)
        if not job:
            raise HTTPException(status_code=404, detail={"error_code": "enrichment_not_found"})
        return {"enrichment_job": job}

    @r.post("/{job_id}/apply")
    async def apply_sheet_job(
        job_id: str,
        body: ApplyBody,
        request: Request,
        workspace_id: str | None = Query(default=None),
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        require_cap(user, "approve")
        ws = _workspace(workspace_id, x_workspace_id, user)
        existing = sheet_service.get_job(ws, job_id)
        if not existing:
            raise HTTPException(status_code=404, detail={"error_code": "enrichment_not_found"})

        gate = gate_or_approve(
            ws,
            kind="sheet.preprocess.apply",
            subject=f"Apply sheet preprocess job {job_id}",
            payload={
                "job_id": job_id,
                "sheet_type": existing.get("sheet_type"),
                "upsert_crm": body.upsert_crm,
                "metrics": existing.get("metrics"),
                "soft_wall_kind_alias": "apply_enrichment",
            },
            object_type="enrichment_job",
            object_id=job_id,
            actor_id=_uid(user),
            force=body.force,
            approval_id=body.approval_id,
        )
        if gate.get("blocked"):
            return {
                "blocked": True,
                "error_code": gate.get("error_code"),
                "approval": gate.get("approval"),
                "correlation_id": _corr(request),
                "deep_link": f"/crm/enrich?job={job_id}",
            }

        try:
            updated = sheet_service.apply_sheet_job(
                ws,
                job_id,
                upsert_crm=body.upsert_crm,
                actor_type="user",
                actor_id=_uid(user),
            )
        except LookupError:
            raise HTTPException(status_code=404, detail={"error_code": "enrichment_not_found"})
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail={"error_code": str(exc) or "not_found"}
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail={"error_code": "apply_failed", "message": str(exc)}
            ) from exc

        crm = (updated.get("apply_result") or {}).get("crm") or {}
        list_id = crm.get("list_id")
        return {
            "blocked": False,
            "enrichment_job": updated,
            "list_id": list_id,
            "list_deep_link": f"/crm/lists/{list_id}" if list_id else None,
            "leads_deep_link": "/crm/leads",
            "deep_link": f"/crm/enrich?job={job_id}",
            "correlation_id": _corr(request),
        }

    @r.get("/{job_id}/download")
    async def download_enriched(
        job_id: str,
        workspace_id: str | None = Query(default=None),
        x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
        user: dict = Depends(get_current_user),
    ) -> FileResponse:
        require_cap(user, "export")
        ws = _workspace(workspace_id, x_workspace_id, user)
        try:
            path = sheet_service.copy_output_for_download(ws, job_id)
        except LookupError:
            raise HTTPException(status_code=404, detail={"error_code": "enrichment_not_found"})
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail={"error_code": "output_not_found"})
        except PermissionError:
            raise HTTPException(status_code=403, detail={"error_code": "path_outside_workspace"})
        return FileResponse(
            path,
            filename=path.name,
            media_type="text/csv",
        )


_register_routes(router)
_register_routes(alias_router)
