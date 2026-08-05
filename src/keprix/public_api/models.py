"""OpenAI-compatible models list endpoint."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from keprix.public_api.auth import check_endpoint_allowed, require_api_key
from keprix.public_api.keys import ApiKeyContext
from keprix.public_api.models_catalog import list_public_models
from keprix.public_api.schemas import ModelListResponse, ModelObject

router = APIRouter(tags=["openai-compat"])


@router.get("/v1/models", response_model=ModelListResponse)
async def list_models(ctx: ApiKeyContext = Depends(require_api_key)) -> ModelListResponse:
    check_endpoint_allowed(ctx, "/v1/models")
    created = int(time.time())
    return ModelListResponse(
        data=[
            ModelObject(id=model_id, created=created, owned_by=owner)
            for model_id, owner in list_public_models()
        ]
    )
