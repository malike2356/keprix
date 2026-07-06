"""Webhook delivery for SDK action plans."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from keprix.sdk.schemas import ActionPlanModel

logger = logging.getLogger(__name__)


async def deliver_plan(webhook_url: str, plan: ActionPlanModel) -> dict[str, Any]:
    payload = plan.model_dump()
    last_error = ""
    async with httpx.AsyncClient(timeout=15.0) as client:
        for attempt in range(3):
            try:
                response = await client.post(webhook_url, json=payload)
                if response.status_code < 500:
                    return {
                        "status": "delivered" if response.status_code < 400 else "failed",
                        "http_status": response.status_code,
                        "attempt": attempt + 1,
                        "body": response.text[:500],
                    }
                last_error = f"HTTP {response.status_code}"
            except Exception as exc:
                last_error = str(exc)
            await asyncio.sleep(2**attempt)
    return {"status": "failed", "error": last_error, "attempts": 3}
