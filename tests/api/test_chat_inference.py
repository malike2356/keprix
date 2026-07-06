"""Tests for web chat inference helpers."""

from __future__ import annotations

import pytest

from keprix.api import chat_inference


def test_list_available_models_prefers_configured_provider(monkeypatch):
    monkeypatch.setenv("KEPRIX_DEFAULT_PROVIDER", "deepseek")
    monkeypatch.setattr(
        chat_inference,
        "_provider_configured",
        lambda provider_id: provider_id == "deepseek",
    )
    models = chat_inference.list_available_models()
    assert models
    assert models[0]["provider"] == "deepseek"
    assert models[0]["id"] == "deepseek:deepseek-chat"


def test_parse_model_id_falls_back_when_provider_missing(monkeypatch):
    monkeypatch.setenv("KEPRIX_DEFAULT_PROVIDER", "deepseek")
    monkeypatch.setattr(
        chat_inference,
        "_provider_configured",
        lambda provider_id: provider_id == "deepseek",
    )
    provider, model = chat_inference.parse_model_id("anthropic:claude-sonnet-4-6")
    assert provider == "deepseek"
    assert model == "deepseek-chat"


@pytest.mark.asyncio
async def test_stream_chat_completion_yields_deltas(monkeypatch):
    monkeypatch.setattr(
        chat_inference,
        "_provider_configured",
        lambda provider_id: provider_id == "deepseek",
    )

    def fake_stream(*, provider, model, messages, out_queue):
        out_queue.put("Hello")
        out_queue.put(" there")
        out_queue.put(None)

    monkeypatch.setattr(chat_inference, "_stream_completion_sync", fake_stream)

    monkeypatch.setattr(chat_inference, "build_codebase_system_prompt", lambda: "system context")

    chunks = []
    async for delta in chat_inference.stream_chat_completion(
        user_text="hi",
        model_id="deepseek:deepseek-chat",
        history=[],
    ):
        chunks.append(delta)

    assert chunks == ["Hello", " there"]
