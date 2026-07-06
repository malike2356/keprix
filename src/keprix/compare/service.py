"""Model response generation for blind comparisons."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

from keprix.api.chat_inference import complete_chat_completion, list_available_models, parse_model_id


@dataclass
class CompareGenerationResult:
    text: str
    latency_ms: int
    model_id: str


class CompareConfigurationError(RuntimeError):
    """Raised when compare cannot run because providers are not configured."""


def configured_model_ids() -> list[str]:
    return [item["id"] for item in list_available_models()]


def validate_model_id(model_id: str) -> str:
    normalized = model_id.strip()
    if not normalized:
        raise ValueError("Model id is required")
    provider, model = parse_model_id(normalized)
    return f"{provider}:{model}"


def pick_random_models(models: list[str] | None = None) -> tuple[str, str]:
    pool = list(models or configured_model_ids())
    pool = [item for item in pool if item.strip()]
    if len(pool) < 2:
        raise CompareConfigurationError(
            "At least two configured models are required. Add LLM provider API keys in Settings."
        )
    return tuple(random.sample(pool, 2))


def resolve_comparison_models(model_a: str | None, model_b: str | None) -> tuple[str, str]:
    if model_a and model_b:
        resolved_a = validate_model_id(model_a)
        resolved_b = validate_model_id(model_b)
        if resolved_a == resolved_b:
            raise ValueError("Choose two different models")
        return resolved_a, resolved_b
    if model_a or model_b:
        raise ValueError("Provide both models or leave both empty for random selection")
    return pick_random_models()


async def generate_response(
    prompt: str,
    model_id: str,
    *,
    user_id: str | None = None,
) -> CompareGenerationResult:
    resolved_id = validate_model_id(model_id)
    result = await complete_chat_completion(
        user_text=prompt,
        model_id=resolved_id,
        user_id=user_id,
        channel="compare",
        include_codebase_context=False,
    )
    return CompareGenerationResult(
        text=result.text,
        latency_ms=result.duration_ms,
        model_id=resolved_id,
    )


async def generate_pair(
    prompt: str,
    model_a: str,
    model_b: str,
    *,
    user_id: str | None = None,
) -> tuple[CompareGenerationResult, CompareGenerationResult]:
    left, right = await asyncio.gather(
        generate_response(prompt, model_a, user_id=user_id),
        generate_response(prompt, model_b, user_id=user_id),
    )
    return left, right
