"""HTTP routes for structured intent extraction."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.backend.intent.engine import get_intent_engine
from keprix.backend.intent.registry import get_intent_registry
from keprix.backend.intent.schemas import IntentExtractionResult, IntentSchema

router = APIRouter(prefix="/api/intent", tags=["intent"])


class ExtractBody(BaseModel):
    translated_text: str = Field(..., min_length=1)
    original_text: str = ""
    source_language: str = "en-GH"
    workspace_id: str = "default"
    conversation_history: list[dict[str, Any]] | None = None


@router.post("/extract")
async def extract_intent(
    body: ExtractBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    del user
    result = await get_intent_engine().extract(
        translated_text=body.translated_text,
        original_text=body.original_text or body.translated_text,
        source_language=body.source_language,
        workspace_id=body.workspace_id,
        conversation_history=body.conversation_history,
    )
    return result.model_dump()


@router.get("/schemas")
async def list_schemas(
    workspace_id: str = Query("default"),
    _user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    schemas = get_intent_registry().get_schemas_for_workspace(workspace_id)
    return [row.model_dump() for row in schemas]


@router.get("/schemas/{domain}")
async def list_domain_schemas(
    domain: str,
    workspace_id: str = Query("default"),
    _user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    schemas = [
        row
        for row in get_intent_registry().get_schemas_for_workspace(workspace_id)
        if row.domain == domain
    ]
    return [row.model_dump() for row in schemas]


@router.post("/register")
async def register_schema(
    body: IntentSchema,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    registry = get_intent_registry()
    registry.register(body)
    return {"ok": True, "intent": body.name, "domain": body.domain}
