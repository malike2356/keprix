"""Compare service helper tests."""

from __future__ import annotations

import pytest

from keprix.compare.service import (
    CompareConfigurationError,
    pick_random_models,
    resolve_comparison_models,
    validate_model_id,
)


def test_validate_model_id_normalizes_provider_model(monkeypatch):
    monkeypatch.setattr(
        "keprix.compare.service.parse_model_id",
        lambda model_id: ("deepseek", "deepseek-chat"),
    )
    assert validate_model_id("deepseek:deepseek-chat") == "deepseek:deepseek-chat"


def test_resolve_comparison_models_rejects_same_model(monkeypatch):
    monkeypatch.setattr(
        "keprix.compare.service.validate_model_id",
        lambda model_id: model_id,
    )
    with pytest.raises(ValueError, match="different models"):
        resolve_comparison_models("deepseek:deepseek-chat", "deepseek:deepseek-chat")


def test_pick_random_models_requires_two_configured(monkeypatch):
    monkeypatch.setattr("keprix.compare.service.configured_model_ids", lambda: ["only:one"])
    with pytest.raises(CompareConfigurationError):
        pick_random_models()


def test_pick_random_models_returns_distinct_pair(monkeypatch):
    monkeypatch.setattr(
        "keprix.compare.service.configured_model_ids",
        lambda: ["a:1", "b:2", "c:3"],
    )
    model_a, model_b = pick_random_models()
    assert model_a != model_b
