"""HTTP routes for Haystack-style RAG pipelines."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.api.auth import require_api_auth
from keprix.rag_pipeline.connectors.notion_token import resolve_notion_token
from keprix.rag_pipeline.connectors.registry import get_connector, list_connectors
from keprix.rag_pipeline.deployment import assess_deployment
from keprix.rag_pipeline.pipeline import get_pipeline_registry

router = APIRouter(prefix="/api/rag-pipeline", tags=["rag-pipeline"])


class IngestBody(BaseModel):
    user_id: str = "default"
    source_type: str = "plaintext"
    source_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    pipeline_id: str = "default"
    store_kind: str = "memory"


class QueryBody(BaseModel):
    user_id: str = "default"
    question: str = Field(..., min_length=1)
    pipeline_id: str = "default"
    source_types: list[str] = Field(default_factory=list)
    hybrid: bool = True
    store_kind: str = "memory"


class NotionIngestBody(BaseModel):
    user_id: str = "default"
    pipeline_id: str = "default"
    store_kind: str = "memory"
    page_ids: list[str] = Field(default_factory=list)
    database_ids: list[str] = Field(default_factory=list)
    token: str | None = None
    max_database_rows: int = 500


@router.get("/connectors")
async def list_rag_connectors(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"connectors": list_connectors()}


@router.get("/stores")
async def list_store_kinds(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {
        "stores": [
            {"kind": "memory", "description": "In-memory test store"},
            {"kind": "sqlite", "description": "Local SQLite chunk store"},
            {"kind": "postgres", "description": "Postgres document store"},
            {"kind": "pgvector", "description": "Postgres with pgvector embeddings"},
            {"kind": "external", "description": "Optional external vector adapter"},
        ]
    }


@router.post("/ingest")
async def ingest_documents(body: IngestBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    registry = get_pipeline_registry()
    pipeline = registry.get_or_create(body.pipeline_id, store_kind=body.store_kind)
    result = await pipeline.ingest(
        user_id=body.user_id,
        source_type=body.source_type,
        source_id=body.source_id,
        content=body.content,
    )
    registry.save_run(result)
    return result.to_dict()


@router.post("/ingest/notion")
async def ingest_notion_source(
    body: NotionIngestBody,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    token = resolve_notion_token(body.token)
    connector = get_connector(
        "notion",
        token=token,
        page_ids=body.page_ids or None,
        database_ids=body.database_ids or None,
        max_database_rows=body.max_database_rows,
    )
    documents = connector.list_documents()
    if not documents:
        raise HTTPException(status_code=400, detail="No Notion pages found to ingest")

    registry = get_pipeline_registry()
    pipeline = registry.get_or_create(body.pipeline_id, store_kind=body.store_kind)
    errors: list[dict[str, str]] = []
    documents_ingested = 0
    last_run_id = ""

    for doc in documents:
        doc_id = str(doc.get("id") or "")
        if not doc_id:
            continue
        try:
            fetched = connector.fetch_document(doc_id)
            result = await pipeline.ingest(
                user_id=body.user_id,
                source_type="notion",
                source_id=fetched["id"],
                content=fetched["content"],
            )
            registry.save_run(result)
            last_run_id = result.run_id
            documents_ingested += 1
        except Exception as exc:
            errors.append({"id": doc_id, "error": str(exc)})

    if documents_ingested == 0:
        raise HTTPException(
            status_code=400,
            detail={"message": "Notion ingest failed for all documents", "errors": errors},
        )

    return {
        "run_id": last_run_id,
        "documents_ingested": documents_ingested,
        "errors": errors,
    }


@router.post("/query")
async def query_pipeline(body: QueryBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    registry = get_pipeline_registry()
    pipeline = registry.get_or_create(body.pipeline_id, store_kind=body.store_kind)
    result = await pipeline.query(
        user_id=body.user_id,
        question=body.question,
        source_types=body.source_types or None,
        hybrid=body.hybrid,
    )
    registry.save_run(result)
    return result.to_dict()


@router.get("/runs")
async def list_pipeline_runs(
    pipeline_id: str | None = None,
    limit: int = 50,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    runs = get_pipeline_registry().list_runs(pipeline_id=pipeline_id, limit=limit)
    return {"runs": [run.to_dict() for run in runs]}


@router.get("/runs/{run_id}")
async def get_pipeline_run(run_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    run = get_pipeline_registry().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run.to_dict()


@router.get("/evaluations")
async def list_evaluations(
    pipeline_id: str | None = None,
    limit: int = 50,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    reports = get_pipeline_registry().eval_store.list_reports(pipeline_id=pipeline_id, limit=limit)
    return {"evaluations": [report.to_dict() for report in reports]}


@router.get("/deployment/{pipeline_id}")
async def deployment_status(pipeline_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    reports = get_pipeline_registry().eval_store.list_reports(pipeline_id=pipeline_id, limit=5)
    report = assess_deployment(pipeline_id=pipeline_id, evaluations=reports)
    return report.to_dict()
