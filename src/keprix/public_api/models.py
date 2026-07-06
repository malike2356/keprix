"""OpenAI-compatible models list endpoint."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from keprix.public_api.auth import require_api_key
from keprix.public_api.keys import ApiKeyContext
from keprix.public_api.models_catalog import list_public_models
from keprix.public_api.schemas import ModelListResponse, ModelObject

router = APIRouter(tags=["openai-compat"])


@router.get("/v1/models", response_model=ModelListResponse)
async def list_models(_ctx: ApiKeyContext = Depends(require_api_key)) -> ModelListResponse:
    created = int(time.time())
    return ModelListResponse(
        data=[
            ModelObject(id=model_id, created=created, owned_by=owner)
            for model_id, owner in list_public_models()
        ]
    )
