"""Shared fixtures for intent extraction tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.backend.intent.registry import reset_intent_registry
from keprix.backend.intent.skill_loader import reset_skill_loader
from keprix.products.loader import reset_products_cache


@pytest.fixture
def intent_env(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_INTENT_HEURISTIC_ONLY", "true")
    monkeypatch.setenv("KEPRIX_ENABLED_PRODUCTS", "example_vertical")
    monkeypatch.setenv("KEPRIX_PRODUCTS_CONFIG", str(repo_root / "config" / "products.example.yaml"))
    reset_products_cache()
    reset_skill_loader(base_dir=tmp_path / "intent")
    reset_intent_registry()
    return tmp_path
