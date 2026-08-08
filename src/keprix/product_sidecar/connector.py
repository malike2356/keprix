"""Southbound ProductConnector: allowlisted HTTP with SSRF and identity guards."""

from __future__ import annotations

import ipaddress
import os
import socket
from typing import Any, Protocol
from urllib.parse import urljoin, urlparse

import httpx

ALLOWED_METHODS = frozenset({"GET", "POST"})
BLOCKED_HOST_LITERALS = frozenset(
    {
        "metadata.google.internal",
        "metadata",
        "169.254.169.254",
    }
)


class ConnectorDenied(Exception):
    pass


class ProductConnector(Protocol):
    """Typed southbound interface used by all product packs."""

    async def health(self) -> dict[str, Any]: ...

    async def capabilities(self) -> dict[str, Any]: ...

    async def token_exchange(self, body: dict[str, Any]) -> dict[str, Any]: ...

    async def context(self, *, purpose: str) -> dict[str, Any]: ...

    async def projected_read(self, operation: str, **params: Any) -> dict[str, Any]: ...

    async def preview(self, operation: str, body: dict[str, Any]) -> dict[str, Any]: ...

    async def action(
        self,
        operation: str,
        body: dict[str, Any],
        *,
        idempotency_key: str = "",
    ) -> dict[str, Any]: ...

    async def ack_event(self, event_id: str) -> dict[str, Any]: ...

    async def delete_subject(self, subject_id: str) -> dict[str, Any]: ...


def _is_private_ip(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def _host_allowlisted(host: str, host_allowlist: list[str] | None) -> bool:
    """Exact match, or suffix match for patterns like ``*.propreneur.test``."""
    if not host_allowlist:
        return True
    host_l = host.lower()
    for pattern in host_allowlist:
        p = pattern.lower().strip()
        if not p:
            continue
        if p.startswith("*."):
            suffix = p[1:]  # ".example.test"
            bare = p[2:]  # "example.test"
            if host_l == bare or host_l.endswith(suffix):
                return True
            continue
        if host_l == p:
            return True
    return False


def assert_safe_url(url: str, *, host_allowlist: list[str] | None = None) -> str:
    """Reject SSRF targets: non-http(s), credentials, DNS rebinding to metadata, etc."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ConnectorDenied("scheme_not_allowed")
    if parsed.username or parsed.password:
        raise ConnectorDenied("credentials_in_url")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ConnectorDenied("missing_host")
    if host in BLOCKED_HOST_LITERALS:
        raise ConnectorDenied("ssrf_blocked_host")
    allow = list(host_allowlist or [])
    if allow and not _host_allowlisted(host, allow):
        raise ConnectorDenied("host_not_allowlisted")
    # Resolve and reject link-local/metadata even if DNS returns them
    try:
        infos = socket.getaddrinfo(host, parsed.port or 80, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ConnectorDenied("dns_resolution_failed") from exc
    for info in infos:
        sockaddr = info[4]
        ip = sockaddr[0]
        if ip in {"169.254.169.254", "::ffff:169.254.169.254"}:
            raise ConnectorDenied("ssrf_metadata")
        # Production egress: only allowlisted hosts; loopback OK for fixtures
        if (
            allow
            and host not in {"127.0.0.1", "localhost"}
            and _is_private_ip(ip)
            and not _host_allowlisted(host, allow)
        ):
            raise ConnectorDenied("ssrf_private_ip")
    return url


class ProductApiConnector:
    """Default-deny HTTP client; only manifest routes may be called."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        routes: list[dict[str, Any]] | None = None,
        host_allowlist: list[str] | None = None,
        base_url_env: str | None = None,
    ) -> None:
        env_name = base_url_env or "CARINA_PRODUCT_API_URL"
        self.base_url = (base_url or os.environ.get(env_name) or "").rstrip("/")
        self.routes = routes or []
        self.host_allowlist = list(host_allowlist or ["127.0.0.1", "localhost"])
        self._idempotent_results: dict[str, dict[str, Any]] = {}
        self._circuit_failures = 0
        self._circuit_open = False

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
        lowered = path.lower()
        if any(x in lowered for x in ("/admin/", "/ops/", "/internal/", ".html", "/login", "..")):
            raise ConnectorDenied("undeclared_or_forbidden")
        if "://" in path or path.startswith("//"):
            raise ConnectorDenied("absolute_url_forbidden")
        matched = self._match(method, path)
        if matched is None:
            raise ConnectorDenied("undeclared_route")
        return matched

    def operation_route(self, operation: str) -> dict[str, Any]:
        for route in self.routes:
            if str(route.get("purpose") or "") == operation or str(route.get("key") or "") == operation:
                return route
        raise ConnectorDenied("undeclared_operation")

    def project_context(self, raw: dict[str, Any], *, purpose: str) -> dict[str, Any]:
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
        if self._circuit_open:
            raise ConnectorDenied("circuit_open")
        route = self.assert_allowed(method, path)
        if idempotency_key and route.get("idempotency") and idempotency_key in self._idempotent_results:
            return dict(self._idempotent_results[idempotency_key])

        if not self.base_url:
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
        assert_safe_url(url, host_allowlist=self.host_allowlist)
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
                res = await client.request(method.upper(), url, headers=headers or {}, json=json_body)
                if res.is_redirect:
                    raise ConnectorDenied("redirect_blocked")
                res.raise_for_status()
                if len(res.content) > 1_000_000:
                    raise ConnectorDenied("response_too_large")
                data = res.json()
                if not isinstance(data, dict):
                    data = {"data": data}
                self._circuit_failures = 0
                if idempotency_key and route.get("idempotency"):
                    self._idempotent_results[idempotency_key] = dict(data)
                return data
        except ConnectorDenied:
            raise
        except Exception as exc:
            self._circuit_failures += 1
            if self._circuit_failures >= 5:
                self._circuit_open = True
            raise ConnectorDenied(f"upstream_error:{type(exc).__name__}") from exc

    async def health(self) -> dict[str, Any]:
        return await self.call("GET", "/api/keprix/v1/health")

    async def capabilities(self) -> dict[str, Any]:
        return await self.call("GET", "/api/keprix/v1/capabilities")

    async def token_exchange(self, body: dict[str, Any]) -> dict[str, Any]:
        return await self.call("POST", "/api/keprix/v1/token/exchange", json_body=body)

    async def context(self, *, purpose: str) -> dict[str, Any]:
        raw = await self.call("GET", "/api/keprix/v1/context")
        return self.project_context(raw, purpose=purpose)

    async def projected_read(self, operation: str, **params: Any) -> dict[str, Any]:
        route = self.operation_route(operation)
        path = str(route["path"])
        for key, value in params.items():
            path = path.replace("{" + key + "}", str(value))
        return await self.call(str(route["method"]), path)

    async def preview(self, operation: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self.action(operation, {**body, "preview": True})

    async def action(
        self,
        operation: str,
        body: dict[str, Any],
        *,
        idempotency_key: str = "",
    ) -> dict[str, Any]:
        route = self.operation_route(operation)
        return await self.call(
            str(route["method"]),
            str(route["path"]),
            json_body=body,
            idempotency_key=idempotency_key,
        )

    async def ack_event(self, event_id: str) -> dict[str, Any]:
        return await self.call(
            "POST",
            "/api/keprix/v1/events/ack",
            json_body={"event_id": event_id},
            idempotency_key=f"ack:{event_id}",
        )

    async def delete_subject(self, subject_id: str) -> dict[str, Any]:
        raise ConnectorDenied("deletion_not_declared")


class FakeProductConnector(ProductApiConnector):
    """In-memory product API fixture reused by pack conformance suites."""

    def __init__(self, *, product_key: str = "fixture") -> None:
        super().__init__(
            base_url="",
            routes=[
                {"method": "GET", "path": "/api/keprix/v1/health", "purpose": "liveness"},
                {"method": "GET", "path": "/api/keprix/v1/capabilities", "purpose": "negotiate"},
                {"method": "POST", "path": "/api/keprix/v1/token/exchange", "purpose": "identity"},
                {"method": "GET", "path": "/api/keprix/v1/context", "purpose": "context_slice"},
                {
                    "method": "POST",
                    "path": "/api/keprix/v1/events/ack",
                    "purpose": "event_ack",
                    "idempotency": True,
                },
                {
                    "method": "POST",
                    "path": "/api/keprix/v1/actions/ping",
                    "purpose": "fixture_action",
                    "idempotency": True,
                },
            ],
            host_allowlist=["127.0.0.1", "localhost"],
        )
        self.product_key = product_key
        self.actions: list[dict[str, Any]] = []

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
            cached = dict(self._idempotent_results[idempotency_key])
            cached["idempotent_replay"] = True
            return cached
        if path.endswith("/health"):
            result = {"ok": True, "product": self.product_key}
        elif path.endswith("/capabilities"):
            result = {"product": self.product_key, "grants": ["ping"], "version": "1.0.0"}
        elif path.endswith("/context"):
            result = {
                "workspace_id": "ws-fixture",
                "product": self.product_key,
                "password": "should-strip",
                "plan": "fixture",
            }
        elif path.endswith("/actions/ping"):
            result = {"ok": True, "echo": (json_body or {}).get("message", "pong")}
            self.actions.append({"path": path, "body": json_body, "idempotency_key": idempotency_key})
        elif path.endswith("/events/ack"):
            result = {"acked": True, "event_id": (json_body or {}).get("event_id")}
        elif path.endswith("/token/exchange"):
            result = {"access_token": "fixture-token", "expires_in": 300}
        else:
            result = {"ok": True, "fixture": True, "path": path}
        if idempotency_key and route.get("idempotency"):
            self._idempotent_results[idempotency_key] = dict(result)
        return result


def connector_from_pack(product_key: str) -> ProductApiConnector:
    from keprix.product_sidecar.registry import get_product_pack_registry

    pack = get_product_pack_registry().require(product_key)
    return ProductApiConnector(
        routes=list(pack.connector.get("routes") or []),
        host_allowlist=list(pack.connector.get("host_allowlist") or ["127.0.0.1", "localhost"]),
        base_url_env=str(pack.connector.get("base_url_env") or ""),
    )


def run_connector_conformance(connector: ProductApiConnector) -> dict[str, Any]:
    """Synchronous-style checklist used by async tests via anyio/asyncio."""
    failures: list[str] = []
    try:
        connector.assert_allowed("GET", "/api/keprix/v1/health")
    except ConnectorDenied:
        failures.append("health_route")
    try:
        connector.assert_allowed("GET", "/admin/secret")
        failures.append("admin_should_deny")
    except ConnectorDenied:
        pass
    try:
        connector.assert_allowed("GET", "http://evil.example/api")
        failures.append("absolute_url_should_deny")
    except ConnectorDenied:
        pass
    try:
        assert_safe_url("http://169.254.169.254/latest/meta-data/", host_allowlist=["127.0.0.1"])
        failures.append("metadata_should_deny")
    except ConnectorDenied:
        pass
    return {"ok": not failures, "failures": failures}
