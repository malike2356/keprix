"""Database pool and migrations for keys.petraclus.uk."""

from __future__ import annotations

import asyncpg

from app.core.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def run_migrations() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS key_accounts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT NOT NULL,
                stripe_customer_id TEXT NOT NULL,
                stripe_subscription_id TEXT NOT NULL UNIQUE,
                product TEXT NOT NULL,
                tier TEXT NOT NULL,
                interval TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS key_accounts_email_idx
                ON key_accounts(email);
            CREATE INDEX IF NOT EXISTS key_accounts_customer_idx
                ON key_accounts(stripe_customer_id);

            CREATE TABLE IF NOT EXISTS licence_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                account_id UUID NOT NULL REFERENCES key_accounts(id) ON DELETE CASCADE,
                key_value TEXT NOT NULL UNIQUE,
                product TEXT NOT NULL,
                tier TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                revoked_at TIMESTAMPTZ
            );

            CREATE INDEX IF NOT EXISTS licence_keys_account_idx
                ON licence_keys(account_id);
            CREATE INDEX IF NOT EXISTS licence_keys_key_idx
                ON licence_keys(key_value);
            """
        )
