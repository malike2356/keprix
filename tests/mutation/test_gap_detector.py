"""Tests for mutation gap detection (Prompt 140)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from keprix.agent.keprix.gap_detector import GapDetector
from keprix.agent.keprix.static_analyser import static_analyser
from keprix.agent.keprix.synthesiser import ToolSynthesiser


@pytest.fixture
def detector() -> GapDetector:
    return GapDetector()


def test_time_tracking_gap_without_tool(detector):
    gap = detector.classify("Track my time on this project", ["todo", "web_search"])
    assert gap.has_gap is True
    assert gap.candidate_tool_name == "track_time"


def test_time_tracking_gap_with_tool_installed(detector):
    gap = detector.classify("Track my time on this project", ["track_time", "todo"])
    assert gap.has_gap is False


def test_general_question_has_no_gap(detector):
    gap = detector.classify("What is 2+2?", ["todo"])
    assert gap.has_gap is False


def test_stock_price_fast_path_still_works(detector):
    gap = detector.classify("fetch AAPL stock price", ["todo"])
    assert gap.has_gap is True
    assert gap.candidate_tool_name == "fetch_stock_price"


def test_mutation_disabled_returns_no_gap(monkeypatch):
    monkeypatch.setenv("KEPRIX_MUTATION_ENABLED", "false")
    from keprix.agent.keprix.config import get_mutation_config

    if hasattr(get_mutation_config, "cache_clear"):
        get_mutation_config.cache_clear()
    gap = GapDetector().classify("Track my time on this project", [])
    assert gap.has_gap is False


@pytest.mark.asyncio
async def test_llm_classifier_returns_gap_when_confident(detector, monkeypatch):
    payload = {
        "has_gap": True,
        "gap_description": "Need a CRM export tool.",
        "candidate_tool_name": "export_crm",
        "candidate_approach": "Call CRM API and return CSV.",
        "confidence": 0.85,
    }

    async def fake_async_call_llm(*_args, **kwargs):
        assert kwargs.get("task") == "mutation_gap_classify"
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    monkeypatch.setattr("agent.auxiliary_client.async_call_llm", fake_async_call_llm)
    monkeypatch.setattr(
        "agent.auxiliary_client.extract_content_or_reasoning",
        lambda response: response.choices[0].message.content,
    )

    gap = await detector.classify_async("export my CRM contacts to CSV", ["todo"])
    assert gap.has_gap is True
    assert gap.candidate_tool_name == "export_crm"
    assert gap.confidence == 0.85


@pytest.mark.asyncio
async def test_llm_classifier_ignores_low_confidence(detector, monkeypatch):
    payload = {
        "has_gap": True,
        "gap_description": "Maybe need a tool.",
        "candidate_tool_name": "maybe_tool",
        "candidate_approach": "Uncertain.",
        "confidence": 0.5,
    }

    async def fake_async_call_llm(*_args, **_kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    monkeypatch.setattr("agent.auxiliary_client.async_call_llm", fake_async_call_llm)
    monkeypatch.setattr(
        "agent.auxiliary_client.extract_content_or_reasoning",
        lambda response: response.choices[0].message.content,
    )

    gap = await detector.classify_async("organise my notes by topic", ["todo"])
    assert gap.has_gap is False
    assert gap.confidence == 0.5


@pytest.mark.asyncio
async def test_track_time_fallback_passes_static_analyser(monkeypatch):
    async def fake_async_call_llm(*_args, **_kwargs):
        raise RuntimeError("no provider")

    monkeypatch.setattr("agent.auxiliary_client.async_call_llm", fake_async_call_llm)

    from keprix.agent.keprix.schemas import GapReport

    gap = GapReport(
        has_gap=True,
        gap_description="No tool exists to track time on projects.",
        candidate_tool_name="track_time",
        candidate_approach="Store time entries with project label.",
        confidence=0.88,
        task="Track my time on this project",
    )
    result = await ToolSynthesiser().synthesise(gap)
    analysis = static_analyser.scan(result.tool_code)
    assert analysis.safe is True
    assert result.tool_name == "track_time"
    assert "project" in result.tool_code
    assert "action" in result.tool_code
