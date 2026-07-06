"""Tests for LLM-powered ToolSynthesiser."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from keprix.agent.keprix.gap_detector import GapDetector
from keprix.agent.keprix.schemas import GapReport
from keprix.agent.keprix.static_analyser import static_analyser
from keprix.agent.keprix.synthesiser import ToolSynthesiser, _extract_json_payload


def _llm_payload(tool_name: str, description: str, *, query_key: str = "message") -> str:
    tool_code = f'''
"""Generated tool: {tool_name}"""
from tools.registry import registry, tool_result, tool_error

def {tool_name}_handler(args, **kwargs):
    value = str(args.get("{query_key}", "")).strip()
    if not value:
        return tool_error("{query_key} is required")
    return tool_result(success=True, {query_key}=value)

registry.register(
    name="{tool_name}",
    toolset="generated",
    schema={{
        "name": "{tool_name}",
        "description": {description!r},
        "parameters": {{
            "type": "object",
            "properties": {{
                "{query_key}": {{"type": "string", "description": "Input"}},
            }},
            "required": ["{query_key}"],
        }},
    }},
    handler={tool_name}_handler,
    emoji="🧬",
)
'''.strip()
    skill_yaml = (
        f"name: {tool_name}\n"
        f"description: {description}\n"
        "triggers:\n"
        f'  - "use {tool_name}"\n'
        "tools:\n"
        f"  - {tool_name}\n"
    )
    return json.dumps(
        {
            "tool_code": tool_code,
            "skill_yaml": skill_yaml,
            "test_input": {query_key: "hello"},
        }
    )


@pytest.mark.asyncio
async def test_synthesiser_uses_llm_response(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_async_call_llm(*_args, **kwargs):
        captured["task"] = kwargs.get("task")
        captured["messages"] = kwargs.get("messages")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=_llm_payload("send_email", "Send email")))]
        )

    monkeypatch.setattr("agent.auxiliary_client.async_call_llm", fake_async_call_llm)
    monkeypatch.setattr(
        "agent.auxiliary_client.extract_content_or_reasoning",
        lambda response: response.choices[0].message.content,
    )

    gap = GapReport(
        has_gap=True,
        gap_description="Send email via configured provider.",
        candidate_tool_name="send_email",
        candidate_approach="Queue an email payload.",
        confidence=0.9,
        task="send email to alice@example.com",
    )
    result = await ToolSynthesiser().synthesise(gap)

    assert captured["task"] == "mutation_synthesis"
    assert result.tool_name == "send_email"
    assert "send_email_handler" in result.tool_code
    assert result.test_input == {"message": "hello"}
    assert static_analyser.scan(result.tool_code).safe is True


@pytest.mark.asyncio
async def test_synthesiser_includes_rewrite_hint_in_prompt(monkeypatch):
    seen: list[str] = []

    async def fake_async_call_llm(*_args, **kwargs):
        messages = kwargs.get("messages") or []
        seen.append(messages[-1]["content"])
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=_llm_payload("safe_tool", "Safe tool", query_key="input"))
                )
            ]
        )

    monkeypatch.setattr("agent.auxiliary_client.async_call_llm", fake_async_call_llm)
    monkeypatch.setattr(
        "agent.auxiliary_client.extract_content_or_reasoning",
        lambda response: response.choices[0].message.content,
    )

    gap = GapReport(
        has_gap=True,
        gap_description="Do a safe thing.",
        candidate_tool_name="safe_tool",
        task="safe task",
    )
    await ToolSynthesiser().synthesise(gap, rewrite_hint="Blocked import: subprocess")

    assert seen
    assert "Blocked import: subprocess" in seen[0]


@pytest.mark.asyncio
async def test_synthesiser_falls_back_when_llm_unavailable(monkeypatch):
    async def failing_call(*_args, **_kwargs):
        raise RuntimeError("No LLM provider configured")

    monkeypatch.setattr("agent.auxiliary_client.async_call_llm", failing_call)

    gap = GapDetector().classify("fetch AAPL stock price", ["todo"])
    result = await ToolSynthesiser().synthesise(gap)

    assert result.tool_name == "fetch_stock_price"
    assert "_MOCK_PRICES" in result.tool_code
    assert result.test_input == {"ticker": "AAPL"}
    assert static_analyser.scan(result.tool_code).safe is True


def test_extract_json_payload_handles_fenced_json():
    raw = '```json\n{"tool_code": "x", "skill_yaml": "y", "test_input": {"a": 1}}\n```'
    payload = _extract_json_payload(raw)
    assert payload == {"tool_code": "x", "skill_yaml": "y", "test_input": {"a": 1}}
