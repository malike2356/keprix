"""Evidence pack HTTP routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.evidence_pack.generator import (
    GovernanceProviderNotConnectedError,
    generate_evidence_pack,
    send_pack_to_provider,
)
from keprix.evidence_pack.store import get_evidence_pack_store

router = APIRouter(prefix="/api/evidence-pack", tags=["evidence-pack"])


def _workspace_id(request: Request) -> str:
    return request.headers.get("x-workspace-id", "default").strip() or "default"


class GenerateBody(BaseModel):
    date_from: str
    date_to: str
    event_types: list[str] | None = None
    include_documents: bool = True
    domain_pack: str | None = None


@router.post("/generate")
async def generate_pack(
    body: GenerateBody,
    request: Request,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    try:
        date_from = datetime.fromisoformat(body.date_from.replace("Z", "+00:00"))
        date_to = datetime.fromisoformat(body.date_to.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid date range") from exc
    pack_id = await generate_evidence_pack(
        workspace_id=workspace_id,
        date_from=date_from,
        date_to=date_to,
        event_types=body.event_types,
        include_documents=body.include_documents,
        domain_pack=body.domain_pack,
    )
    return {"pack_id": pack_id, "status": "ready"}


@router.get("")
async def list_packs(
    request: Request,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    rows = get_evidence_pack_store().list_for_workspace(workspace_id)
    return {
        "packs": [
            {
                **row.to_dict(),
                "download_url": f"/api/evidence-pack/{row.pack_id}/download",
            }
            for row in sorted(rows, key=lambda item: item.generated_at, reverse=True)
        ]
    }


@router.get("/{pack_id}")
async def get_pack(
    pack_id: str,
    request: Request,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    record = get_evidence_pack_store().get(pack_id)
    if record is None or record.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Evidence pack not found")
    return {
        **record.to_dict(),
        "download_url": f"/api/evidence-pack/{pack_id}/download",
    }


@router.get("/{pack_id}/download")
async def download_pack(
    pack_id: str,
    request: Request,
    _admin: dict = Depends(require_admin),
) -> FileResponse:
    workspace_id = _workspace_id(request)
    store = get_evidence_pack_store()
    record = store.get(pack_id)
    if record is None or record.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Evidence pack not found")
    path = store.zip_path(pack_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Evidence pack file missing")
    return FileResponse(path, media_type="application/zip", filename=f"evidence-pack-{pack_id}.zip")


@router.post("/{pack_id}/send-to-provider")
async def send_to_provider(
    pack_id: str,
    request: Request,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    record = get_evidence_pack_store().get(pack_id)
    if record is None or record.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Evidence pack not found")
    try:
        return await send_pack_to_provider(pack_id)
    except GovernanceProviderNotConnectedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
