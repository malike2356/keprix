"""Document agent HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from keprix.api.auth import require_api_auth
from keprix.documents.connector_registry import list_connectors
from keprix.documents.document_agent import get_document_agent
from keprix.documents.index_manager import get_index_manager
from keprix.documents.structured_extract import SCHEMAS
from keprix.documents.workflow import run_query_workflow

router = APIRouter(prefix="/api/documents", tags=["documents"])


class CreateIndexBody(BaseModel):
    name: str = Field(..., min_length=1)
    user_id: str = "default"


class QueryBody(BaseModel):
    user_id: str = "default"
    question: str = Field(..., min_length=1)
    index_id: str | None = None
    source_types: list[str] = Field(default_factory=list)
    evidence_first: bool = True


class ExtractBody(BaseModel):
    text: str = Field(..., min_length=1)
    schema_name: str = "generic"


@router.get("/connectors")
async def document_connectors(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"connectors": list_connectors(), "schemas": sorted(SCHEMAS.keys())}


@router.post("/indexes")
async def create_index(body: CreateIndexBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    index = get_document_agent().create_index(user_id=body.user_id, name=body.name)
    return index.to_dict()


@router.get("/indexes")
async def list_indexes(user_id: str = "default", _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    indexes = get_index_manager().list_indexes(user_id)
    return {"indexes": [index.to_dict() for index in indexes]}


@router.get("/indexes/{index_id}")
async def inspect_index(index_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    try:
        return get_document_agent().explain_index(index_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Index not found") from exc


@router.post("/indexes/{index_id}/refresh")
async def refresh_index(index_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    try:
        return await get_index_manager().refresh_index(index_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Index not found") from exc


@router.delete("/indexes/{index_id}")
async def delete_index(index_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    deleted = await get_index_manager().delete_index(index_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Index not found")
    return {"deleted": True, "index_id": index_id}


@router.post("/indexes/{index_id}/upload")
async def upload_document(
    index_id: str,
    file: UploadFile = File(...),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    content = await file.read()
    try:
        return await get_document_agent().upload_and_index(
            index_id,
            filename=file.filename or "upload.txt",
            content=content,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Index not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/query")
async def query_documents(body: QueryBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    if body.index_id:
        index = get_index_manager().get(body.index_id)
        if index is None:
            raise HTTPException(status_code=404, detail="Index not found")
        body.user_id = index.user_id
    return await run_query_workflow(
        user_id=body.user_id,
        question=body.question,
        source_types=body.source_types or None,
        evidence_first=body.evidence_first,
    )


@router.post("/extract")
async def extract_document(body: ExtractBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    try:
        return await get_document_agent().extract(text=body.text, schema_name=body.schema_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
