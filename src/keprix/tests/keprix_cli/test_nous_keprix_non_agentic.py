"""Tests for the Nous-Keprix-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"keprix"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``keprix-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "keprix" tag namespace.

``is_nous_keprix_non_agentic`` should only match the actual Nous Research
Keprix-3 / Keprix-4 chat family.
"""

from __future__ import annotations

import pytest

from keprix_cli.model_switch import (
    _KEPRIX_MODEL_WARNING,
    _check_keprix_model_warning,
    is_nous_keprix_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "NousResearch/Keprix-3-Llama-3.1-70B",
        "NousResearch/Keprix-3-Llama-3.1-405B",
        "keprix-3",
        "Keprix-3",
        "keprix-4",
        "keprix-4-405b",
        "keprix_4_70b",
        "openrouter/keprix3:70b",
        "openrouter/nousresearch/keprix-4-405b",
        "NousResearch/Keprix3",
        "keprix-3.1",
    ],
)
def test_matches_real_nous_keprix_chat_models(model_name: str) -> None:
    assert is_nous_keprix_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Keprix 3/4"
    )
    assert _check_keprix_model_warning(model_name) == _KEPRIX_MODEL_WARNING


@pytest.mark.parametrize(
    "model_name",
    [
        # Kyle's local Modelfile — qwen3:14b under a custom tag
        "keprix-brain:qwen3-14b-ctx16k",
        "keprix-brain:qwen3-14b-ctx32k",
        "keprix-honcho:qwen3-8b-ctx8k",
        # Plain unrelated models
        "qwen3:14b",
        "qwen3-coder:30b",
        "qwen2.5:14b",
        "claude-opus-4-6",
        "anthropic/claude-sonnet-4.5",
        "gpt-5",
        "openai/gpt-4o",
        "google/gemini-2.5-flash",
        "deepseek-chat",
        # Non-chat Keprix models we don't warn about
        "keprix-llm-2",
        "keprix2-pro",
        "nous-keprix-2-mistral",
        # Edge cases
        "",
        "keprix",  # bare "keprix" isn't the 3/4 family
        "keprix-brain",
        "brain-keprix-3-impostor",  # "3" not preceded by /: boundary
    ],
)
def test_does_not_match_unrelated_models(model_name: str) -> None:
    assert not is_nous_keprix_non_agentic(model_name), (
        f"expected {model_name!r} NOT to be flagged as Nous Keprix 3/4"
    )
    assert _check_keprix_model_warning(model_name) == ""


def test_none_like_inputs_are_safe() -> None:
    assert is_nous_keprix_non_agentic("") is False
    # Defensive: the helper shouldn't crash on None-ish falsy input either.
    assert _check_keprix_model_warning("") == ""
