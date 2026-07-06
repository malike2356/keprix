"""Stripe REST client (httpx) with local mock mode for tests."""

from __future__ import annotations

import os
import uuid
from typing import Any

import httpx


class StripeError(RuntimeError):
    pass


class StripeClient:
    def __init__(self, *, api_key: str | None = None, test_mode: bool | None = None) -> None:
        self.api_key = (api_key or os.environ.get("STRIPE_SECRET_KEY", "")).strip()
        self.test_mode = test_mode if test_mode is not None else os.environ.get("STRIPE_TEST_MODE", "").lower() in {
            "1",
            "true",
            "yes",
        }
        self._mock = not self.api_key
        self._base = "https://api.stripe.com/v1"

    @property
    def mock_mode(self) -> bool:
        return self._mock

    async def _request(self, method: str, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._mock:
            return self._mock_response(method, path, data or {})
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                f"{self._base}{path}",
                data=data,
                headers=headers,
            )
        if response.status_code >= 400:
            raise StripeError(response.text)
        return response.json()

    def _mock_response(self, method: str, path: str, data: dict[str, Any]) -> dict[str, Any]:
        if path == "/products" and method == "POST":
            return {"id": f"prod_{uuid.uuid4().hex[:12]}", "name": data.get("name", "product")}
        if path == "/prices" and method == "POST":
            return {
                "id": f"price_{uuid.uuid4().hex[:12]}",
                "unit_amount": int(data.get("unit_amount", 0)),
                "currency": data.get("currency", "gbp"),
                "recurring": {"interval": data.get("recurring[interval]", "month")},
            }
        if path == "/checkout/sessions" and method == "POST":
            return {
                "id": f"cs_{uuid.uuid4().hex[:12]}",
                "url": "https://checkout.stripe.test/session/mock",
                "customer": data.get("customer") or f"cus_{uuid.uuid4().hex[:12]}",
            }
        if path == "/billing_portal/sessions" and method == "POST":
            return {"id": f"bps_{uuid.uuid4().hex[:12]}", "url": "https://billing.stripe.test/portal/mock"}
        if path == "/customers" and method == "POST":
            return {"id": f"cus_{uuid.uuid4().hex[:12]}", "email": data.get("email", "")}
        return {"id": f"mock_{uuid.uuid4().hex[:8]}"}

    async def create_product(self, *, name: str, metadata: dict[str, str]) -> dict[str, Any]:
        payload = {"name": name}
        for key, value in metadata.items():
            payload[f"metadata[{key}]"] = value
        return await self._request("POST", "/products", payload)

    async def create_price(
        self,
        *,
        product_id: str,
        unit_amount: int,
        currency: str,
        interval: str | None,
        metadata: dict[str, str],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "product": product_id,
            "unit_amount": unit_amount,
            "currency": currency,
        }
        if interval:
            payload["recurring[interval]"] = interval
        for key, value in metadata.items():
            payload[f"metadata[{key}]"] = value
        return await self._request("POST", "/prices", payload)

    async def create_customer(self, *, email: str, metadata: dict[str, str]) -> dict[str, Any]:
        payload = {"email": email}
        for key, value in metadata.items():
            payload[f"metadata[{key}]"] = value
        return await self._request("POST", "/customers", payload)

    async def create_checkout_session(
        self,
        *,
        customer_id: str | None,
        price_id: str,
        success_url: str,
        cancel_url: str,
        trial_days: int = 0,
        metadata: dict[str, str],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "mode": "subscription",
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        if customer_id:
            payload["customer"] = customer_id
        if trial_days > 0:
            payload["subscription_data[trial_period_days]"] = str(trial_days)
        for key, value in metadata.items():
            payload[f"metadata[{key}]"] = value
        return await self._request("POST", "/checkout/sessions", payload)

    async def create_portal_session(self, *, customer_id: str, return_url: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/billing_portal/sessions",
            {"customer": customer_id, "return_url": return_url},
        )


_client: StripeClient | None = None


def get_stripe_client() -> StripeClient:
    global _client
    if _client is None:
        _client = StripeClient()
    return _client
