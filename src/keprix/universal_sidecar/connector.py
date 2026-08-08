"""Configured project API connectors (KUS-04). Default-deny, SSRF-safe."""

from __future__ import annotations

import ipaddress
import socket
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from keprix.universal_sidecar.registry import get_project_registry

BLOCKED_NETWORKS = (
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


class ConnectorError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ProjectConnector:
    """Compile-only declared operations: project.read('order.get', params)."""

    def __init__(self, project_key: str) -> None:
        self.project_key = project_key
        self._idempotent: dict[str, dict[str, Any]] = {}
        self._circuit_failures = 0
        self._circuit_open_until = 0.0
        self._rate: dict[str, list[float]] = {}

    def _manifest(self) -> dict[str, Any]:
        row = get_project_registry().require(self.project_key)
        return row["manifest"]

    def _ops(self) -> dict[str, dict[str, Any]]:
        return {str(op["key"]): op for op in (self._manifest().get("connectors") or [])}

    def _check_host(self, url: str) -> None:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        egress = self._manifest().get("egress") or {}
        allow_private = bool(egress.get("allow_private_networks"))
        allow_loopback = bool(egress.get("allow_loopback"))
        allowed_hosts = set(egress.get("allowed_hosts") or [])
        if allowed_hosts and host not in allowed_hosts:
            # Also allow base_url host
            base_host = urlparse(str(self._manifest().get("base_url") or "")).hostname
            if host != base_host:
                raise ConnectorError("denied", f"host not allowlisted: {host}")
        try:
            infos = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise ConnectorError("dns", f"DNS resolution failed for {host}") from exc
        for info in infos:
            ip_str = info[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue
            for net in BLOCKED_NETWORKS:
                if ip in net:
                    if ip.is_loopback and allow_loopback:
                        continue
                    if (ip.is_private or ip.is_link_local) and allow_private:
                        continue
                    raise ConnectorError("ssrf", f"blocked address {ip_str}")

    def _rate_ok(self, op_key: str, limit: int) -> bool:
        now = time.time()
        bucket = self._rate.setdefault(op_key, [])
        self._rate[op_key] = [t for t in bucket if now - t < 60]
        if len(self._rate[op_key]) >= limit:
            return False
        self._rate[op_key].append(now)
        return True

    def call(
        self,
        operation_key: str,
        params: dict[str, Any] | None = None,
        *,
        idempotency_key: str = "",
        mode: str | None = None,
    ) -> dict[str, Any]:
        if get_project_registry().is_killed(self.project_key, switch="connector"):
            raise ConnectorError("killed", "connector kill switch")
        if time.time() < self._circuit_open_until:
            raise ConnectorError("circuit_open", "circuit open")
        ops = self._ops()
        op = ops.get(operation_key)
        if not op:
            raise ConnectorError("unknown_operation", f"undeclared operation {operation_key}")
        if mode and op.get("mode") != mode and mode == "apply":
            raise ConnectorError("denied", "apply not declared for operation")
        if op.get("mode") == "apply" and not idempotency_key:
            raise ConnectorError("validation", "Idempotency-Key required for apply")
        if idempotency_key and idempotency_key in self._idempotent:
            prior = self._idempotent[idempotency_key]
            if prior.get("operation") == operation_key and prior.get("params") == (params or {}):
                return dict(prior["result"])
            raise ConnectorError("conflict", "idempotency key reused with different input")

        rate = int(op.get("rate_per_minute") or 60)
        if not self._rate_ok(operation_key, rate):
            raise ConnectorError("rate_limited", "operation rate exceeded")

        path_template = str(op["path"])
        # Safe param substitution: only {name} placeholders, no traversal
        path = path_template
        for k, v in (params or {}).items():
            token = "{" + k + "}"
            if token in path:
                safe = str(v)
                if ".." in safe or "/" in safe or "\\" in safe or "?" in safe or "#" in safe:
                    raise ConnectorError("validation", f"unsafe path parameter {k}")
                path = path.replace(token, safe)
        if "{" in path:
            raise ConnectorError("validation", "unresolved path parameters")

        base = str(self._manifest().get("base_url") or "").rstrip("/")
        url = urljoin(base + "/", path.lstrip("/"))
        # Prevent host override via params
        if urlparse(url).hostname != urlparse(base).hostname:
            raise ConnectorError("denied", "host override blocked")
        self._check_host(url)

        method = str(op["method"]).upper()
        timeout = float(op.get("timeout_seconds") or 15)
        headers = {"Accept": "application/json", "X-Keprix-Project": self.project_key}
        # Auth via vault refs only (resolved by caller env); never return secrets
        auth = self._manifest().get("auth") or {}
        vault_ref = str(auth.get("vault_ref") or "")
        if vault_ref.startswith("env:"):
            import os

            token = os.environ.get(vault_ref[4:], "")
            if token and auth.get("profile") == "bearer":
                headers["Authorization"] = f"Bearer {token}"
            elif token and auth.get("profile") == "static_header":
                headers[str(auth.get("header_name") or "X-Api-Key")] = token

        try:
            with httpx.Client(timeout=timeout, follow_redirects=False) as client:
                resp = client.request(method, url, headers=headers, json=params if method != "GET" else None)
                # Manual single redirect check
                if resp.is_redirect:
                    loc = resp.headers.get("location") or ""
                    self._check_host(urljoin(url, loc))
                    raise ConnectorError("redirect", "redirects require explicit re-validation; denied by default")
                if resp.status_code >= 500:
                    self._circuit_failures += 1
                    if self._circuit_failures >= 5:
                        self._circuit_open_until = time.time() + 30
                    raise ConnectorError("upstream", f"status {resp.status_code}")
                self._circuit_failures = 0
                content_type = resp.headers.get("content-type", "")
                if "json" not in content_type and resp.content:
                    raise ConnectorError("schema", "unexpected content type")
                max_bytes = 1_000_000
                if len(resp.content) > max_bytes:
                    raise ConnectorError("schema", "response too large")
                data = resp.json() if resp.content else {}
        except ConnectorError:
            raise
        except Exception as exc:
            self._circuit_failures += 1
            raise ConnectorError("upstream", str(exc)) from exc

        result = {
            "operation": operation_key,
            "status_code": resp.status_code,
            "data": data,
            "mode": op.get("mode", "read"),
        }
        if idempotency_key:
            self._idempotent[idempotency_key] = {
                "operation": operation_key,
                "params": dict(params or {}),
                "result": result,
            }
        return result

    def read(self, operation_key: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.call(operation_key, params, mode="read")


def get_connector(project_key: str) -> ProjectConnector:
    return ProjectConnector(project_key)
