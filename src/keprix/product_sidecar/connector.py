"""Southbound allowlisted connector to Carina/Aiva product API."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urljoin

import httpx

ALLOWED_METHODS = frozenset({"GET", "POST"})


class ConnectorDenied(Exception):
    pass


class ProductApiConnector:
    """Default-deny HTTP client; only manifest routes may be called."""

    def __init__(self, *, base_url: str | None = None, routes: list[dict[str, Any]] | None = None) -> None:
        self.base_url = (base_url or os.environ.get("CARINA_PRODUCT_API_URL") or "").rstrip("/")
        self.routes = routes or []
        self._idempotent_results: dict[str, dict[str, Any]] = {}

    def _match(self, method: str, path: str) -> dict[str, Any] | None:
        method_u = method.upper()
        for route in self.routes:
            if str(route.get("method", "")).upper() != method_u:
                continue
            template = str(route.get("path") or "")
            if self._path_matches(template, path):
                return route
        return None

    @staticmethod
    def _path_matches(template: str, path: str) -> bool:
        t_parts = template.strip("/").split("/")
        p_parts = path.strip("/").split("/")
        if len(t_parts) != len(p_parts):
            return False
        for t, p in zip(t_parts, p_parts):
            if t.startswith("{") and t.endswith("}"):
                continue
            if t != p:
                return False
        return True

    def assert_allowed(self, method: str, path: str) -> dict[str, Any]:
        if method.upper() not in ALLOWED_METHODS:
            raise ConnectorDenied("method_not_allowed")
        # Block obvious admin / UI scrape paths
        lowered = path.lower()
        if any(x in lowered for x in ("/admin/", "/ops/", "/internal/", ".html", "/login")):
            raise ConnectorDenied("undeclared_or_forbidden")
        matched = self._match(method, path)
        if matched is None:
            raise ConnectorDenied("undeclared_route")
        return matched

    def project_context(self, raw: dict[str, Any], *, purpose: str) -> dict[str, Any]:
        """Purpose-limited context slice; strip sensitive fields."""
        allowed = {
            "workspace_id",
            "workspace_name",
            "actor_id",
            "entitlements",
            "soft_wall_pending_count",
            "plan",
            "product",
        }
        sensitive = {"password", "token", "secret", "api_key", "ssn", "card_number"}
        out: dict[str, Any] = {"purpose": purpose}
        for key, value in raw.items():
            if key in sensitive:
                continue
            if key in allowed:
                out[key] = value
        return out

    async def call(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        idempotency_key: str = "",
    ) -> dict[str, Any]:
        route = self.assert_allowed(method, path)
        if idempotency_key and route.get("idempotency") and idempotency_key in self._idempotent_results:
            return dict(self._idempotent_results[idempotency_key])

        if not self.base_url:
            # Local fixture response for undeployed product API
            result = {
                "ok": True,
                "fixture": True,
                "path": path,
                "method": method.upper(),
                "body": json_body or {},
            }
            if idempotency_key and route.get("idempotency"):
                self._idempotent_results[idempotency_key] = dict(result)
            return result

        url = urljoin(self.base_url + "/", path.lstrip("/"))
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.request(method.upper(), url, headers=headers or {}, json=json_body)
            res.raise_for_status()
            data = res.json()
            if not isinstance(data, dict):
                data = {"data": data}
            if idempotency_key and route.get("idempotency"):
                self._idempotent_results[idempotency_key] = dict(data)
            return data


def connector_from_pack(product_key: str) -> ProductApiConnector:
    from keprix.product_sidecar.registry import get_product_pack_registry

    pack = get_product_pack_registry().require(product_key)
    return ProductApiConnector(routes=list(pack.connector.get("routes") or []))
