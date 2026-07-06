"""Model comparison HTTP routes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from keprix.api.chat_inference import list_available_models
from keprix.compare.service import (
    CompareConfigurationError,
    generate_pair,
    resolve_comparison_models,
)
from keprix.compare.store import get_compare_store
from keprix.security.validation import default_validator

router = APIRouter(prefix="/api/compare", tags=["compare"])


def _user_id(request: Request) -> str:
    return request.headers.get("x-user-id", "").strip() or "local"


class CompareStartBody(BaseModel):
    prompt: str = Field(..., min_length=1)
    model_a: str | None = None
    model_b: str | None = None
    random_models: bool = True

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        return default_validator.validate_string(value, "prompt")


class VoteBody(BaseModel):
    winner: Literal["a", "b", "tie"]


@router.get("/models")
async def compare_models() -> dict[str, Any]:
    models = list_available_models()
    return {"models": models, "count": len(models)}


@router.post("/start")
async def start_comparison(body: CompareStartBody, request: Request) -> dict[str, Any]:
    store = get_compare_store()
    user = _user_id(request)
    try:
        if body.random_models and not body.model_a and not body.model_b:
            model_a, model_b = resolve_comparison_models(None, None)
        else:
            model_a, model_b = resolve_comparison_models(body.model_a, body.model_b)
    except CompareConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    try:
        result_a, result_b = await generate_pair(body.prompt, model_a, model_b, user_id=user)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    record = store.create(
        user_id=user,
        prompt=body.prompt,
        model_a=result_a.model_id,
        model_b=result_b.model_id,
        response_a=result_a.text,
        response_b=result_b.text,
        latency_ms_a=result_a.latency_ms,
        latency_ms_b=result_b.latency_ms,
    )
    return {
        "comparison_id": record.id,
        "response_a": result_a.text,
        "response_b": result_b.text,
        "latency_ms_a": result_a.latency_ms,
        "latency_ms_b": result_b.latency_ms,
    }


@router.post("/{comparison_id}/vote")
async def vote(comparison_id: str, body: VoteBody, request: Request) -> dict[str, Any]:
    store = get_compare_store()
    user = _user_id(request)
    record = store.vote(comparison_id, user, body.winner)
    if record is None:
        raise HTTPException(404, "Comparison not found or already voted")
    return {
        "comparison_id": record.id,
        "winner": record.winner,
        "model_a": record.model_a,
        "model_b": record.model_b,
        "latency_ms_a": record.latency_ms_a,
        "latency_ms_b": record.latency_ms_b,
    }


@router.get("/history")
async def history(request: Request) -> list[dict[str, Any]]:
    store = get_compare_store()
    user = _user_id(request)
    return [
        {
            "id": record.id,
            "prompt": record.prompt[:200],
            "model_a": record.model_a,
            "model_b": record.model_b,
            "winner": record.winner,
            "voted_at": record.voted_at.isoformat() if record.voted_at else None,
            "created_at": record.created_at.isoformat(),
            "latency_ms_a": record.latency_ms_a,
            "latency_ms_b": record.latency_ms_b,
        }
        for record in store.list_for_user(user)
    ]


@router.get("/leaderboard")
async def leaderboard() -> dict[str, Any]:
    store = get_compare_store()
    pairs = store.leaderboard()
    models = store.model_leaderboard()
    return {"pairs": pairs, "models": models}
