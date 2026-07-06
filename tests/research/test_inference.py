"""Unit tests for deep research LLM inference wiring."""

from __future__ import annotations

import pytest

from keprix.api.chat_inference import ChatCompletionResult
from keprix.research.errors import ResearchConfigError, ResearchPipelineError
from keprix.research import inference as research_inference


@pytest.mark.asyncio
async def test_complete_research_prompt_uses_workspace_provider(monkeypatch):
    async def fake_complete(**kwargs):
        assert kwargs["channel"] == "research"
        assert kwargs["include_codebase_context"] is False
        return ChatCompletionResult(
            text="Structured findings about boreholes.",
            provider="deepseek",
            model="deepseek-chat",
            duration_ms=12,
        )

    monkeypatch.setattr("keprix.research.inference.complete_chat_completion", fake_complete)
    text = await research_inference.complete_research_prompt(
        "Write a report",
        model="deepseek-chat",
        user_id="user-1",
    )
    assert text == "Structured findings about boreholes."


@pytest.mark.asyncio
async def test_complete_research_prompt_surfaces_provider_config_errors(monkeypatch):
    async def fake_complete(**kwargs):
        raise RuntimeError(
            "Provider 'deepseek' is not configured. Add its API key to .env and restart the backend."
        )

    monkeypatch.setattr("keprix.research.inference.complete_chat_completion", fake_complete)
    with pytest.raises(ResearchConfigError, match="not configured"):
        await research_inference.complete_research_prompt("Write a report")


@pytest.mark.asyncio
async def test_complete_research_prompt_rejects_empty_output(monkeypatch):
    async def fake_complete(**kwargs):
        return ChatCompletionResult(text="   ", provider="deepseek", model="deepseek-chat", duration_ms=1)

    monkeypatch.setattr("keprix.research.inference.complete_chat_completion", fake_complete)
    with pytest.raises(ResearchPipelineError, match="empty research response"):
        await research_inference.complete_research_prompt("Write a report")
