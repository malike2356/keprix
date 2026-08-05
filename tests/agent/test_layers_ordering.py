"""Layered prompt builder tests (prompt 289)."""

from __future__ import annotations

from agent.layered_prompt import LayeredPromptBuilder, PromptLayer


def test_layers_are_ordered():
    builder = LayeredPromptBuilder()
    builder.add_layer(PromptLayer.TONE, "tone content")
    builder.add_layer(PromptLayer.IDENTITY, "identity content")
    prompt = builder.build()
    assert prompt.index("<identity>") < prompt.index("<tone>")


def test_missing_layers_are_omitted():
    builder = LayeredPromptBuilder()
    builder.add_layer(PromptLayer.SAFETY, "safety only")
    prompt = builder.build()
    assert "<safety>" in prompt
    assert "<identity>" not in prompt
