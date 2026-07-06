"""Export HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from keprix.api.auth import require_api_auth
from keprix.export.renderer import export_document
from keprix.export.resolver import make_document_resolver
from keprix.export.store import get_export_store

router = APIRouter(prefix="/api/export", tags=["export"])


class ExportRequest(BaseModel):
    title: str = "Export"
    markdown: str = ""
    content: str = ""
    input_type: str = "markdown"
    document_type: str = ""
    version: str = ""
    prepared_by: str = ""
    classification: str = ""
    format: str = "html"
    include_cover: bool = False
    include_signatory: bool = False
    signatory_data: dict[str, Any] | None = None


def _cover_data(body: ExportRequest) -> dict[str, Any]:
    return {
        "document_type": body.document_type,
        "version": body.version,
        "prepared_by": body.prepared_by,
        "classification": body.classification,
    }


def _source(body: ExportRequest) -> str:
    return body.content or body.markdown


def _render_export(body: ExportRequest, user_key: str) -> dict[str, Any]:
    raw = _source(body)
    if not raw and body.input_type not in ("document_id", "note_id"):
        raise HTTPException(status_code=400, detail="content or markdown is required")
    resolver = None
    if body.input_type in ("document_id", "note_id"):
        resolver = make_document_resolver(user_key)
    try:
        return export_document(
            title=body.title,
            input_type=body.input_type,
            content=raw,
            format=body.format,
            include_cover=body.include_cover,
            cover_data=_cover_data(body),
            include_signatory=body.include_signatory,
            signatory_data=body.signatory_data,
            document_resolver=resolver,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("")
async def create_export(
    body: ExportRequest,
    user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    result = _render_export(body, user)
    fmt_returned = result.get("format_returned", result["format"])
    store = get_export_store()
    record = store.save(
        title=body.title,
        content=result["content"],
        mime=result["mime"],
        format_returned=fmt_returned,
    )
    return {
        "file_id": record.file_id,
        "file_url": f"/api/export/{record.file_id}",
        "format_returned": fmt_returned,
        "filename": record.filename,
        "size_bytes": record.size_bytes,
    }


@router.post("/download")
async def download_export(
    body: ExportRequest,
    user: str = Depends(require_api_auth),
) -> Response:
    result = _render_export(body, user)
    mime = result["mime"]
    content = result["content"]
    fmt_returned = result.get("format_returned", result["format"])
    if isinstance(content, str):
        return Response(content=content, media_type=mime)
    filename = f"{body.title.replace(' ', '_')}.{fmt_returned}"
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{file_id}")
async def get_export_file(
    file_id: str,
    _user: str = Depends(require_api_auth),
) -> FileResponse:
    path = get_export_store().resolve_path(file_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Export not found")
    record = get_export_store().get(file_id)
    filename = record.filename if record else path.name
    media_type = record.mime if record else "application/octet-stream"
    return FileResponse(
        path,
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{file_id}/inline")
async def get_export_inline(
    file_id: str,
    _user: str = Depends(require_api_auth),
) -> FileResponse:
    path = get_export_store().resolve_path(file_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Export not found")
    record = get_export_store().get(file_id)
    filename = record.filename if record else path.name
    media_type = record.mime if record else "text/html"
    return FileResponse(
        path,
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
