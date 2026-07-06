"""Tests for playbook model benchmarking."""

from __future__ import annotations

import pytest

from keprix.playbook.benchmark import _estimate_benchmark, run_model_benchmark
from keprix.playbook.model_catalog import get_model


@pytest.mark.asyncio
async def test_run_model_benchmark_falls_back_when_ollama_unavailable(monkeypatch):
    async def fail_ollama(*_args, **_kwargs):
        return None

    monkeypatch.setattr("keprix.playbook.benchmark._benchmark_ollama", fail_ollama)
    result = await run_model_benchmark("llama3.1-8b-q4")
    assert result["source"] == "estimated"
    assert result["latency_ms"] > 0
    assert result["tokens_per_sec"] > 0


def test_estimate_benchmark_uses_catalog_scores():
    model = get_model("smollm-1.7b-q4")
    assert model is not None
    result = _estimate_benchmark(model, "ollama")
    assert result["model_id"] == model.id
    assert result["tokens_per_sec"] > 0
