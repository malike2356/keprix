"""Tests for mutation tool synthesizer (Prompt 150)."""

from __future__ import annotations

import textwrap
from types import SimpleNamespace

import pytest

from keprix.improvement.tool_gap_detector import ToolGapProposal
from keprix.mutation.tool_synthesizer import (
    SynthesisResult,
    _extract_source_from_response,
    synthesize_tool,
)

_GOOD_TOOL = textwrap.dedent(
    '''
    from tools.registry import registry, tool_result, tool_error

    def fetch_weather_handler(args, **kwargs):
        city = str(args.get("city", "")).strip()
        if not city:
            return tool_error("city is required")
        return tool_result(success=True, city=city, weather="sunny")

    registry.register(
        name="fetch_weather",
        toolset="generated",
        schema={
            "name": "fetch_weather",
            "description": "Fetches weather",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
        handler=fetch_weather_handler,
    )
    '''
).strip() + "\n"

_BAD_TOOL = "def fetch_weather_handler(args, **kwargs):\n    raise RuntimeError('nope')\n"


@pytest.mark.asyncio
async def test_synthesize_simple_tool_returns_valid_source(monkeypatch):
    calls = {"count": 0}

    async def fake_llm(**kwargs):
        calls["count"] += 1
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=_GOOD_TOOL))],
            usage=SimpleNamespace(total_tokens=42),
        )

    monkeypatch.setattr("agent.auxiliary_client.async_call_llm", fake_llm)
    monkeypatch.setattr(
        "agent.auxiliary_client.extract_content_or_reasoning",
        lambda response: response.choices[0].message.content,
    )

    proposal = ToolGapProposal(
        proposal_id="p1",
        tool_name="fetch_weather",
        description="Fetches current weather for a city from a free API",
        confidence=0.9,
    )
    result = await synthesize_tool(proposal, "default", max_attempts=1)
    assert isinstance(result, SynthesisResult)
    assert result.success is True
    assert "fetch_weather_handler" in result.source_code
    assert result.sandbox_result is not None
    assert result.sandbox_result.passed is True


@pytest.mark.asyncio
async def test_retries_on_sandbox_failure(monkeypatch):
    responses = [_BAD_TOOL, _GOOD_TOOL]
    calls = {"count": 0}

    async def fake_llm(**kwargs):
        idx = min(calls["count"], len(responses) - 1)
        calls["count"] += 1
        content = responses[idx]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(total_tokens=10),
        )

    monkeypatch.setattr("agent.auxiliary_client.async_call_llm", fake_llm)
    monkeypatch.setattr(
        "agent.auxiliary_client.extract_content_or_reasoning",
        lambda response: response.choices[0].message.content,
    )

    proposal = ToolGapProposal(
        proposal_id="p2",
        tool_name="fetch_weather",
        description="weather",
        confidence=0.9,
    )
    result = await synthesize_tool(proposal, "default", max_attempts=3)
    assert result.success is True
    assert result.attempts == 2


@pytest.mark.asyncio
async def test_returns_failure_after_max_attempts(monkeypatch):
    async def fake_llm(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=_BAD_TOOL))],
            usage=SimpleNamespace(total_tokens=5),
        )

    monkeypatch.setattr("agent.auxiliary_client.async_call_llm", fake_llm)
    monkeypatch.setattr(
        "agent.auxiliary_client.extract_content_or_reasoning",
        lambda response: response.choices[0].message.content,
    )

    proposal = ToolGapProposal(
        proposal_id="p3",
        tool_name="fetch_weather",
        description="weather",
        confidence=0.9,
    )
    result = await synthesize_tool(proposal, "default", max_attempts=2)
    assert result.success is False
    assert result.attempts == 2
    assert result.error


def test_extracts_source_strips_code_fences():
    raw = "```python\nprint('ok')\n```"
    assert _extract_source_from_response(raw).strip() == "print('ok')"
