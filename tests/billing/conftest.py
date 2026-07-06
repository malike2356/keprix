"""Shared fixtures for billing tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG = ROOT / "config" / "billing.example.yaml"


@pytest.fixture(autouse=True)
def billing_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_BILLING_CONFIG", str(EXAMPLE_CONFIG))
    monkeypatch.setenv("KEPRIX_BILLING_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_BILLING_ALLOW_UNSIGNED_WEBHOOKS", "true")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path / "keprix-data"))
    billing_dir = tmp_path / "keprix-data" / "billing"
    billing_dir.mkdir(parents=True, exist_ok=True)
    for name in ("customers", "subscriptions", "invoices", "seats", "webhook_events", "stripe_map"):
        (billing_dir / f"{name}.json").write_text("{}", encoding="utf-8")

    from keprix.billing import config_loader
    from keprix.billing.store import BillingStore
    import keprix.billing.store as billing_store_module
    from keprix.billing.stripe import client as stripe_client

    config_loader._CONFIG = None
    config_loader._CONFIG_PATH = None
    stripe_client._client = None

    billing_store_module._store = BillingStore(base_dir=billing_dir)
    store = billing_store_module._store
    yield store
