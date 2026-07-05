from __future__ import annotations

import os
import re
import sys
from types import SimpleNamespace

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import stripe

from app import db
from app.billing import handle_checkout_completed, handle_subscription_deleted
from app.core.config import settings
from app.core.key_generator import generate_key


@pytest_asyncio.fixture
async def database(monkeypatch: pytest.MonkeyPatch):
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for billing persistence tests")

    monkeypatch.setattr(settings, "database_url", database_url)
    await db.close_pool()
    await db.run_migrations()
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE licence_keys, key_accounts RESTART IDENTITY CASCADE")

    yield pool

    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE licence_keys, key_accounts RESTART IDENTITY CASCADE")
    await db.close_pool()


def test_key_generation_produces_expected_prefix_and_checksum_format() -> None:
    petra = generate_key("petraclus", "TEAM")
    assert re.match(r"^PETRA-TEAM-[A-Z0-9]{8}-[A-Z0-9]{8}-[A-F0-9]{2}$", petra)


@pytest.mark.asyncio
async def test_checkout_with_known_price_persists_account_and_key(
    database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_PRICE_PETRA_PRO_MONTHLY", "price_petra_pro")
    monkeypatch.setattr(
        stripe.Subscription,
        "retrieve",
        lambda subscription_id: {
            "id": subscription_id,
            "items": {"data": [{"price": {"id": "price_petra_pro"}}]},
        },
    )
    monkeypatch.setattr("app.billing._send_key_email", _noop_send_key_email)

    await handle_checkout_completed(
        SimpleNamespace(
            subscription="sub_known",
            customer="cus_known",
            customer_email="buyer@example.com",
        )
    )

    async with database.acquire() as conn:
        account = await conn.fetchrow(
            "SELECT * FROM key_accounts WHERE stripe_subscription_id = $1",
            "sub_known",
        )
        key = await conn.fetchrow(
            "SELECT * FROM licence_keys WHERE account_id = $1",
            account["id"],
        )

    assert account["email"] == "buyer@example.com"
    assert account["product"] == "petraclus"
    assert account["tier"] == "PRO"
    assert account["status"] == "active"
    assert key["key_value"].startswith("PETRA-PRO-")
    assert key["status"] == "active"


@pytest.mark.asyncio
async def test_checkout_with_unknown_price_does_nothing(
    database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.delenv("STRIPE_PRICE_PETRA_PRO_MONTHLY", raising=False)
    monkeypatch.setattr(
        stripe.Subscription,
        "retrieve",
        lambda subscription_id: {
            "id": subscription_id,
            "items": {"data": [{"price": {"id": "price_unknown"}}]},
        },
    )

    await handle_checkout_completed(
        SimpleNamespace(
            subscription="sub_unknown",
            customer="cus_unknown",
            customer_email="buyer@example.com",
        )
    )

    async with database.acquire() as conn:
        account_count = await conn.fetchval("SELECT count(*) FROM key_accounts")
        key_count = await conn.fetchval("SELECT count(*) FROM licence_keys")

    assert account_count == 0
    assert key_count == 0


@pytest.mark.asyncio
async def test_subscription_deleted_revokes_all_active_keys(
    database,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_PRICE_PETRA_PRO_MONTHLY", "price_petra_pro")
    monkeypatch.setattr(
        stripe.Subscription,
        "retrieve",
        lambda subscription_id: {
            "id": subscription_id,
            "items": {"data": [{"price": {"id": "price_petra_pro"}}]},
        },
    )
    monkeypatch.setattr("app.billing._send_key_email", _noop_send_key_email)

    await handle_checkout_completed(
        SimpleNamespace(
            subscription="sub_cancelled",
            customer="cus_cancelled",
            customer_email="buyer@example.com",
        )
    )
    await handle_subscription_deleted(SimpleNamespace(id="sub_cancelled"))

    async with database.acquire() as conn:
        account_status = await conn.fetchval(
            "SELECT status FROM key_accounts WHERE stripe_subscription_id = $1",
            "sub_cancelled",
        )
        key_status = await conn.fetchval(
            """
            SELECT lk.status
            FROM licence_keys lk
            JOIN key_accounts ka ON ka.id = lk.account_id
            WHERE ka.stripe_subscription_id = $1
            """,
            "sub_cancelled",
        )

    assert account_status == "cancelled"
    assert key_status == "revoked"


async def _noop_send_key_email(*, email: str, product: str, tier: str, key_value: str) -> None:
    return None
