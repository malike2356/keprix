"""Admin endpoints for licence key operations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.db import get_pool

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def _redact_key(key_value: str) -> str:
    return f"{key_value[:12]}***"


@router.get("/keys")
async def list_keys(email: str, x_admin_token: str | None = Header(default=None)) -> dict:
    require_admin(x_admin_token)
    pool = await get_pool()
    async with pool.acquire() as conn:
        accounts = await conn.fetch(
            """
            SELECT *
            FROM key_accounts
            WHERE lower(email) = lower($1)
            ORDER BY created_at DESC
            """,
            email,
        )
        account_ids = [row["id"] for row in accounts]
        keys_by_account: dict[str, list[dict[str, Any]]] = {}
        if account_ids:
            keys = await conn.fetch(
                """
                SELECT *
                FROM licence_keys
                WHERE account_id = ANY($1::uuid[])
                ORDER BY issued_at DESC
                """,
                account_ids,
            )
            for key in keys:
                key_dict = _to_dict(key)
                key_dict["key_value"] = _redact_key(str(key_dict["key_value"]))
                keys_by_account.setdefault(str(key["account_id"]), []).append(key_dict)

    return {
        "accounts": [
            {
                **_to_dict(account),
                "keys": keys_by_account.get(str(account["id"]), []),
            }
            for account in accounts
        ]
    }


@router.get("/keys/lookup")
async def lookup_key(key: str, x_admin_token: str | None = Header(default=None)) -> dict:
    require_admin(x_admin_token)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                ka.id AS account_id,
                ka.email,
                ka.stripe_customer_id,
                ka.stripe_subscription_id,
                ka.product AS account_product,
                ka.tier AS account_tier,
                ka.interval,
                ka.status AS account_status,
                lk.id AS key_id,
                lk.key_value,
                lk.product AS key_product,
                lk.tier AS key_tier,
                lk.status AS key_status,
                lk.issued_at,
                lk.revoked_at
            FROM licence_keys lk
            JOIN key_accounts ka ON ka.id = lk.account_id
            WHERE lk.key_value = $1
            """,
            key,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Key not found")

    body = _to_dict(row)
    body["key_value"] = _redact_key(str(body["key_value"]))
    return body


@router.post("/keys/{account_id}/revoke")
async def revoke_account_keys(account_id: str, x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
    require_admin(x_admin_token)
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            account = await conn.fetchrow(
                """
                UPDATE key_accounts
                SET status = 'cancelled', updated_at = now()
                WHERE id = $1::uuid
                RETURNING id, email
                """,
                account_id,
            )
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")
            result = await conn.execute(
                """
                UPDATE licence_keys
                SET status = 'revoked', revoked_at = now()
                WHERE account_id = $1::uuid AND status = 'active'
                """,
                account_id,
            )

    revoked_count = int(result.split(" ")[-1])
    return {
        "account_id": str(account["id"]),
        "email": account["email"],
        "revoked": revoked_count,
    }
