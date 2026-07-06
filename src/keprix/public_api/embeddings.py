"""OpenAI-compatible embeddings endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from keprix.memory.embeddings import EMBEDDING_DIM, EmbeddingService
from keprix.public_api.auth import check_endpoint_allowed, check_model_allowed, require_api_key
from keprix.public_api.keys import ApiKeyContext
from keprix.public_api.rate_limits import enforce_rate_limit
from keprix.public_api.schemas import EmbeddingData, EmbeddingRequest, EmbeddingResponse, UsageInfo
from keprix.public_api.usage import record_api_usage

router = APIRouter(tags=["openai-compat"])

_embedding_service = EmbeddingService()


@router.post("/v1/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(
    body: EmbeddingRequest,
    request: Request,
    ctx: ApiKeyContext = Depends(require_api_key),
) -> EmbeddingResponse:
    check_endpoint_allowed(ctx, "/v1/embeddings")
    check_model_allowed(ctx, body.model)
    enforce_rate_limit(request, ctx)

    inputs = [body.input] if isinstance(body.input, str) else list(body.input)
    vectors = await _embedding_service.embed_many(inputs)
    data = [
        EmbeddingData(index=i, embedding=vector)
        for i, vector in enumerate(vectors)
    ]
    prompt_tokens = sum(max(1, len(text.split())) for text in inputs)
    await record_api_usage(
        ctx,
        endpoint="/v1/embeddings",
        model=body.model,
        prompt_tokens=prompt_tokens,
        completion_tokens=0,
    )
    return EmbeddingResponse(
        data=data,
        model=body.model,
        usage=UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            total_tokens=prompt_tokens,
        ),
    )


def embedding_dimensions() -> int:
    return EMBEDDING_DIM
