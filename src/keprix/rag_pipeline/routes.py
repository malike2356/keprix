"""HTTP routes for Haystack-style RAG pipelines."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from keprix.api.auth import require_api_auth
from keprix.rag_pipeline.connectors.files import LocalFileSourceConnector, UrlSourceConnector
from keprix.rag_pipeline.connectors.notion_token import resolve_notion_token
from keprix.rag_pipeline.connectors.registry import get_connector, list_connectors
from keprix.rag_pipeline.deployment import assess_deployment
from keprix.rag_pipeline.pipeline import get_pipeline_registry

router = APIRouter(prefix="/api/rag-pipeline", tags=["rag-pipeline"])

DEFAULT_PIPELINE_ID = os.getenv("KEPRIX_RAG_DEFAULT_PIPELINE_ID", "production-default")


class IngestBody(BaseModel):
    user_id: str = "default"
    source_type: str = "plaintext"
    source_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    pipeline_id: str = DEFAULT_PIPELINE_ID
    store_kind: str = "memory"


class QueryBody(BaseModel):
    user_id: str = "default"
    question: str = Field(..., min_length=1)
    pipeline_id: str = DEFAULT_PIPELINE_ID
    source_types: list[str] = Field(default_factory=list)
    hybrid: bool = True
    store_kind: str = "memory"


class NotionIngestBody(BaseModel):
    user_id: str = "default"
    pipeline_id: str = DEFAULT_PIPELINE_ID
    store_kind: str = "memory"
    page_ids: list[str] = Field(default_factory=list)
    database_ids: list[str] = Field(default_factory=list)
    token: str | None = None
    max_database_rows: int = 500


class PathIngestBody(BaseModel):
    user_id: str = "default"
    pipeline_id: str = DEFAULT_PIPELINE_ID
    store_kind: str = "memory"
    path: str = Field(..., min_length=1)
    vault_relative: bool = False


class UrlIngestBody(BaseModel):
    user_id: str = "default"
    pipeline_id: str = DEFAULT_PIPELINE_ID
    store_kind: str = "memory"
    url: str = Field(..., min_length=1)


class CreatePipelineBody(BaseModel):
    pipeline_id: str = Field(..., min_length=1)
    store_kind: str = "memory"


def _vault_root() -> Path | None:
    for key in ("KEPRIX_VAULT_PATH", "KEPRIX_OBSIDIAN_VAULT", "KEPRIX_DATA_DIR"):
        raw = os.getenv(key, "").strip()
        if raw:
            path = Path(raw).expanduser()
            if key == "KEPRIX_DATA_DIR":
                path = path / "vault"
            return path
    home = Path.home() / ".keprix" / "vault"
    return home if home.exists() else None


@router.get("/config")
async def rag_config(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    registry = get_pipeline_registry()
    pipelines = list(getattr(registry, "_pipelines", {}).keys()) if hasattr(registry, "_pipelines") else []
    return {"default_pipeline_id": DEFAULT_PIPELINE_ID, "pipelines": pipelines}


@router.get("/connectors")
async def list_rag_connectors(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"connectors": list_connectors()}


@router.get("/stores")
async def list_store_kinds(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    registry = get_pipeline_registry()
    counts: dict[str, int] = {}
    for run in registry.list_runs(limit=500):
        payload = run.to_dict() if hasattr(run, "to_dict") else {}
        kind = str(payload.get("store_kind") or "memory")
        counts[kind] = counts.get(kind, 0) + 1
    stores = [
        {
            "kind": "memory",
            "description": "In-memory test store",
            "run_count": counts.get("memory", 0),
            "count_label": "runs",
        },
        {
            "kind": "sqlite",
            "description": "Local SQLite chunk store",
            "run_count": counts.get("sqlite", 0),
            "count_label": "runs",
        },
        {
            "kind": "postgres",
            "description": "Postgres document store",
            "run_count": counts.get("postgres", 0),
            "count_label": "runs",
        },
        {
            "kind": "pgvector",
            "description": "Postgres with pgvector embeddings",
            "run_count": counts.get("pgvector", 0),
            "count_label": "runs",
        },
        {
            "kind": "external",
            "description": "Optional external vector adapter",
            "run_count": counts.get("external", 0),
            "count_label": "runs",
        },
    ]
    return {"stores": stores}


@router.post("/pipelines")
async def create_pipeline(body: CreatePipelineBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    get_pipeline_registry().get_or_create(body.pipeline_id, store_kind=body.store_kind)
    return {"pipeline_id": body.pipeline_id, "store_kind": body.store_kind, "ok": True}


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


@router.post("/ingest/path")
async def ingest_path_source(body: PathIngestBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    vault_root = str(_vault_root()) if body.vault_relative else None
    try:
        fetched = LocalFileSourceConnector(body.path, vault_root=vault_root).fetch_document()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    registry = get_pipeline_registry()
    pipeline = registry.get_or_create(body.pipeline_id, store_kind=body.store_kind)
    result = await pipeline.ingest(
        user_id=body.user_id,
        source_type=str(fetched.get("source_type") or "plaintext"),
        source_id=str(fetched.get("id") or body.path),
        content=str(fetched.get("content") or ""),
    )
    registry.save_run(result)
    return result.to_dict()


@router.post("/ingest/url")
async def ingest_url_source(body: UrlIngestBody, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    try:
        fetched = UrlSourceConnector(body.url).fetch_document()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    registry = get_pipeline_registry()
    pipeline = registry.get_or_create(body.pipeline_id, store_kind=body.store_kind)
    result = await pipeline.ingest(
        user_id=body.user_id,
        source_type=str(fetched.get("source_type") or "plaintext"),
        source_id=str(fetched.get("id") or body.url),
        content=str(fetched.get("content") or ""),
    )
    registry.save_run(result)
    return result.to_dict()


@router.post("/ingest/file")
async def ingest_uploaded_file(
    _user: str = Depends(require_api_auth),
    file: UploadFile = File(...),
    pipeline_id: str = Form(default=DEFAULT_PIPELINE_ID),
    store_kind: str = Form(default="memory"),
    user_id: str = Form(default="default"),
) -> dict[str, Any]:
    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Only UTF-8 text/markdown uploads are supported") from exc
    filename = Path(file.filename or "upload.txt").name
    source_type = "markdown" if filename.lower().endswith((".md", ".markdown")) else "plaintext"
    registry = get_pipeline_registry()
    pipeline = registry.get_or_create(pipeline_id, store_kind=store_kind)
    result = await pipeline.ingest(
        user_id=user_id,
        source_type=source_type,
        source_id=filename,
        content=content,
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
    q: str | None = None,
    limit: int = 50,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    runs = get_pipeline_registry().list_runs(pipeline_id=pipeline_id, limit=max(limit, 200))
    payloads = [run.to_dict() for run in runs]
    if q:
        needle = q.strip().lower()
        payloads = [
            item
            for item in payloads
            if needle in str(item.get("run_id") or "").lower()
            or needle in str(item.get("answer") or "").lower()
            or needle in str(item.get("route") or "").lower()
            or needle in str((item.get("metadata") or {}).get("question") or "").lower()
        ]
    return {"runs": payloads[:limit]}


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
    payload = report.to_dict()
    payload["plain"] = (
        "Ready for production traffic."
        if payload.get("ready")
        else "Gated: evaluation thresholds not met yet. Run a few queries and check eval precision/faithfulness."
    )
    return payload
