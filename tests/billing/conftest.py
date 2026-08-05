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
    monkeypatch.delenv("KEPRIX_BILLING_PROVIDER", raising=False)
    monkeypatch.setenv("KEPRIX_BILLING_ALLOW_UNSIGNED_WEBHOOKS", "true")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    for key in (
        "STRIPE_SECRET_KEY",
        "STRIPE_SECRET",
        "STRIPE_KEY",
        "STRIPE_BILLING_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "STRIPE_BILLING_WEBHOOK_SECRET",
        "STRIPE_PUBLISHABLE_KEY",
        "STRIPE_BILLING_PUBLISHABLE_KEY",
    ):
        monkeypatch.setenv(key, "")
    # Prevent create_app() from reloading keprix/.env over test env.
    monkeypatch.setattr(
        "keprix_cli.env_loader.load_keprix_dotenv",
        lambda *args, **kwargs: False,
    )
    price_file = tmp_path / "stripe-prices.md"
    price_file.write_text(
        "\n".join(
            [
                "Pro (£49/mo): price_test_pro_month",
                "Pro (£490/yr): price_test_pro_year",
                "Team (£129/mo): price_test_team_month",
                "Team (£1290/yr): price_test_team_year",
                "Extra Seats (£15/mo): price_test_extra_seats_month",
                "Single Sign-On (£99/mo): price_test_sso_month",
                "£1/one-off: price_test_donation_one_off",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("KEPRIX_STRIPE_CREDENTIALS_FILE", str(price_file))
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
