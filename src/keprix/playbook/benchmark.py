"""Quick latency benchmark for local model backends."""

from __future__ import annotations

import time
from typing import Any

import httpx

from keprix.playbook.model_catalog import CatalogModel, get_model


async def _benchmark_ollama(model_id: str, *, port: int = 11434, host: str = "127.0.0.1") -> dict[str, Any] | None:
    url = f"http://{host}:{port}/api/generate"
    payload = {
        "model": model_id,
        "prompt": "Reply with one short sentence.",
        "stream": False,
        "options": {"num_predict": 32},
    }
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, OSError, ValueError):
        return None

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    eval_count = int(body.get("eval_count") or 0)
    eval_duration_ns = int(body.get("eval_duration") or 0)
    if eval_duration_ns > 0 and eval_count > 0:
        tokens_per_sec = round(eval_count / (eval_duration_ns / 1_000_000_000), 2)
    else:
        tokens_per_sec = round(max(eval_count, 1) / max(latency_ms / 1000, 0.001), 2)

    return {
        "model_id": model_id,
        "backend": "ollama",
        "latency_ms": latency_ms,
        "tokens_per_sec": tokens_per_sec,
        "source": "live",
        "port": port,
    }


def _estimate_benchmark(model: CatalogModel, backend: str) -> dict[str, Any]:
    size_factor = max(model.size_b, 1.0)
    latency_ms = round(80 + (size_factor * 12), 2)
    tokens_per_sec = round((model.benchmark_score / 10.0) * (8.0 / size_factor), 2)
    return {
        "model_id": model.id,
        "backend": backend,
        "latency_ms": latency_ms,
        "tokens_per_sec": tokens_per_sec,
        "source": "estimated",
        "note": "Live backend unavailable; values derived from catalog fit data.",
    }


async def run_model_benchmark(model_id: str, backend: str = "ollama", *, port: int = 11434) -> dict[str, Any]:
    model = get_model(model_id)
    if model is None:
        raise ValueError(f"Unknown model `{model_id}`")

    if backend == "ollama":
        live = await _benchmark_ollama(model_id, port=port)
        if live is not None:
            return live

    return _estimate_benchmark(model, backend)
