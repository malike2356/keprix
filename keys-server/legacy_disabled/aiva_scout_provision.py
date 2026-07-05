"""Disabled legacy Aiva Scout provisioning helpers.

This code is kept only as historical reference. keys.petraclus.uk must not call
commercial Aiva provisioning flows.
"""

import secrets
from typing import Any

import httpx

from app.core.config import settings


def issue_scout_api_key() -> str:
    return f"scout_live_{secrets.token_hex(24)}"


async def provision_aiva_scout_workspace(
    *,
    account_email: str,
    aiva_workspace_id: str,
    tier: str,
) -> dict[str, Any] | None:
    if not settings.scout_provision_secret:
        return None

    license_key = issue_scout_api_key()
    payload = {
        "email": account_email.strip().lower(),
        "carinaTenantId": aiva_workspace_id,
        "licenseKey": license_key,
        "plan": "scout_pro",
        "product": "carina-aiva",
        "tier": tier,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            settings.scout_provision_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-Scout-Provision-Secret": settings.scout_provision_secret,
            },
        )
        if response.status_code not in (200, 201):
            return None
        body = response.json()
        dashboard_url = f"{settings.scout_console_public_url.rstrip('/')}/account"
        return {
            "workspace_id": aiva_workspace_id,
            "api_key": license_key,
            "dashboard_url": dashboard_url,
            "scout_account_id": body.get("accountId"),
            "setup_token": body.get("setupToken"),
        }


async def notify_aiva_core_scout_linked(
    *,
    workspace_id: str,
    tier: str,
    account_email: str,
) -> None:
    if not settings.aiva_core_webhook_url:
        return
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            settings.aiva_core_webhook_url,
            json={
                "workspaceId": workspace_id,
                "tier": tier,
                "email": account_email,
            },
        )
