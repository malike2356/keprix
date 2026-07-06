from __future__ import annotations

from typing import Any

import httpx

from keprix_sdk.domain import Domain
from keprix_sdk.schema import domain_to_json
from keprix_sdk.types import ActionPlan, ActionStep


class KeprixSdkClient:
    def __init__(self, base_url: str, api_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self._headers = {"Authorization": f"Bearer {api_token}"}

    async def register_app(
        self,
        *,
        name: str,
        version: str,
        domain: Domain,
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "name": name,
            "version": version,
            "domain": domain_to_json(domain),
            "webhook_url": webhook_url,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/sdk/apps/register",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def execute(self, app_id: str, message: str, session_id: str | None = None) -> ActionPlan:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/sdk/execute",
                headers=self._headers,
                json={"app_id": app_id, "message": message, "session_id": session_id},
            )
            response.raise_for_status()
            return _plan_from_json(response.json())

    async def confirm(self, plan_id: str, confirmed: bool = True) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/sdk/execute/confirm",
                headers=self._headers,
                json={"plan_id": plan_id, "confirmed": confirmed},
            )
            response.raise_for_status()
            return response.json()


def _plan_from_json(data: dict[str, Any]) -> ActionPlan:
    steps = [
        ActionStep(
            entity=step["entity"],
            operation=step["operation"],
            fields=dict(step.get("fields") or {}),
            missing_fields=list(step.get("missing_fields") or []),
            confirmation_required=bool(step.get("confirmation_required")),
            confidence=float(step.get("confidence") or 0.0),
            result=step.get("result"),
        )
        for step in data.get("steps", [])
    ]
    return ActionPlan(
        user_input=data.get("user_input", ""),
        session_id=data.get("session_id"),
        steps=steps,
        requires_confirmation=bool(data.get("requires_confirmation")),
        confirmation_prompt=data.get("confirmation_prompt") or "",
        plan_id=data.get("plan_id"),
    )
