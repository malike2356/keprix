"""Shared fixtures for localization tests that rely on product config assets."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.backend.localization.glossary import reset_glossary_service
from keprix.products.loader import reset_products_cache


@pytest.fixture(autouse=True)
def abbis_product_env(monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("KEPRIX_ENABLED_PRODUCTS", "abbis_borehole")
    monkeypatch.setenv("KEPRIX_PRODUCTS_CONFIG", str(repo_root / "config" / "products.example.yaml"))
    reset_products_cache()
    reset_glossary_service()
    yield
    reset_glossary_service()
    reset_products_cache()
