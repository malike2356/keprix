"""Export HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from keprix.api.auth import require_api_auth
from keprix.export.renderer import export_document

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


@router.post("")
async def create_export(
    body: ExportRequest,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    raw = _source(body)
    if not raw:
        raise HTTPException(status_code=400, detail="content or markdown is required")
    try:
        result = export_document(
            title=body.title,
            input_type=body.input_type,
            content=raw,
            format=body.format,
            include_cover=body.include_cover,
            cover_data=_cover_data(body),
            include_signatory=body.include_signatory,
            signatory_data=body.signatory_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    fmt_returned = result.get("format_returned", result["format"])
    if fmt_returned == "pdf":
        return {
            "format_returned": fmt_returned,
            "size_bytes": len(result["content"]),
            "filename": f"{body.title.replace(' ', '_')}.pdf",
        }
    return {
        "format_returned": fmt_returned,
        "content": result["content"],
        "filename": f"{body.title.replace(' ', '_')}.{fmt_returned}",
    }


@router.post("/download")
async def download_export(
    body: ExportRequest,
    _user: str = Depends(require_api_auth),
) -> Response:
    raw = _source(body)
    if not raw:
        raise HTTPException(status_code=400, detail="content or markdown is required")
    try:
        result = export_document(
            title=body.title,
            input_type=body.input_type,
            content=raw,
            format=body.format,
            include_cover=body.include_cover,
            cover_data=_cover_data(body),
            include_signatory=body.include_signatory,
            signatory_data=body.signatory_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
