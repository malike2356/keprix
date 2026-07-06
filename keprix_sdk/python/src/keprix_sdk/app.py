from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from keprix_sdk.client import KeprixSdkClient
from keprix_sdk.domain import Domain
from keprix_sdk.types import ActionPlan, ExecutionResult


class KeprixApp:
    def __init__(
        self,
        name: str,
        keprix_url: str,
        api_token: str,
        *,
        carina_url: str | None = None,
    ) -> None:
        self.name = name
        self.keprix_url = (carina_url or keprix_url).rstrip("/")
        self.api_token = api_token
        self.version = "1.0.0"
        self._domains: list[Domain] = []
        self._client = KeprixSdkClient(self.keprix_url, api_token)
        self._app_id: str | None = None
        self._webhook_url: str | None = None
        self._action_callback: Callable[[ActionPlan], Awaitable[ExecutionResult] | ExecutionResult] | None = None

    def register_domain(self, domain: Domain) -> None:
        self._domains.append(domain)

    def on_action(self, callback: Callable[[ActionPlan], Awaitable[ExecutionResult] | ExecutionResult]) -> Callable:
        self._action_callback = callback
        return callback

    async def connect(self, webhook_url: str | None = None) -> str:
        self._webhook_url = webhook_url
        domain = self._domains[0] if self._domains else Domain(name="default", entities=[])
        result = await self._client.register_app(
            name=self.name,
            version=self.version,
            domain=domain,
            webhook_url=webhook_url,
        )
        self._app_id = result["app_id"]
        return self._app_id

    async def handle(self, text: str, session_id: str | None = None) -> ActionPlan:
        if not self._app_id:
            await self.connect(self._webhook_url)
        assert self._app_id
        return await self._client.execute(self._app_id, text, session_id=session_id)

    async def confirm(self, plan_id: str, confirmed: bool = True) -> dict[str, Any]:
        return await self._client.confirm(plan_id, confirmed=confirmed)

    async def start(self) -> None:
        await self.connect(self._webhook_url)
        if not self._action_callback:
            while True:
                await asyncio.sleep(3600)

        while True:
            await asyncio.sleep(1)


CarinaApp = KeprixApp
