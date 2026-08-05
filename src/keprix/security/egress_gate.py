"""EgressGate: httpx transport wrapper that enforces per-product egress policy.

Tools must never create bare httpx.AsyncClient instances directly.
They should use get_http_client() from keprix.http_client instead, which
returns a gate-enforced client.

The gate:
  1. Resolves the destination hostname to an IP address (async DNS).
  2. Calls EgressPolicy.is_allowed(product_id, host, ip).
  3. If denied: raises EgressBlocked and logs the block to EgressAuditLog.
  4. If allowed: forwards the request and logs the allow.

DNS results are cached per host for the lifetime of the client (per-request
cache via the transport instance). This keeps overhead under 2ms after the
first lookup.
"""

from __future__ import annotations

import asyncio
import socket
import logging
from typing import Any, Callable

import httpx

from .egress_audit import EgressAuditLog, get_egress_audit
from .egress_policy import EgressDecision, EgressPolicy, get_egress_policy
from .product_context import get_product_context_or_none
from .scout_control import egress_force_blocked
from .scout_integration import emit_egress_blocked_signal

logger = logging.getLogger(__name__)


class EgressBlocked(Exception):
    """Raised when an outbound request is denied by egress policy."""

    def __init__(self, product_id: str, host: str, ip: str, reason: str) -> None:
        self.product_id = product_id
        self.host = host
        self.ip = ip
        self.reason = reason
        super().__init__(
            f"Outbound request to {host} ({ip}) blocked for product "
            f"'{product_id}': {reason}. "
            f"Add '{host}' to allowed_hosts in {product_id}/keprix.yaml."
        )


# Type alias for DNS resolver: (hostname) -> ip_string
DNSResolver = Callable[[str], str]


async def _default_resolve(host: str) -> str:
    """Resolve hostname to its first A/AAAA record IP string."""
    loop = asyncio.get_event_loop()
    infos = await loop.run_in_executor(
        None,
        lambda: socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM),
    )
    if infos:
        return infos[0][4][0]   # (family, type, proto, canonname, sockaddr) -> ip
    return host  # fallback: return hostname; policy will fail-closed if not IP


class EgressGateTransport(httpx.AsyncBaseTransport):
    """httpx transport that enforces egress policy before forwarding requests."""

    def __init__(
        self,
        product_id: str,
        policy: EgressPolicy,
        audit: EgressAuditLog,
        resolve_fn: DNSResolver | None = None,
        inner: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.product_id = product_id
        self.policy = policy
        self.audit = audit
        self._resolve = resolve_fn or _default_resolve
        self._inner = inner or httpx.AsyncHTTPTransport()
        self._dns_cache: dict[str, str] = {}

    async def _resolve_cached(self, host: str) -> str:
        if host not in self._dns_cache:
            self._dns_cache[host] = await self._resolve(host)
        return self._dns_cache[host]

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        url_str = str(request.url)

        if egress_force_blocked():
            await self.audit.log_block(
                self.product_id, host, "", url_str, "scout_egress_force_blocked"
            )
            emit_egress_blocked_signal(
                product_id=self.product_id,
                host=host,
                ip="",
                reason="scout_egress_force_blocked",
            )
            raise EgressBlocked(
                product_id=self.product_id,
                host=host,
                ip="",
                reason="scout_egress_force_blocked",
            )

        try:
            ip = await self._resolve_cached(host)
        except Exception as exc:
            logger.warning("DNS resolution failed for %s: %s", host, exc)
            ip = host  # fail closed via policy unknown-ip handling

        decision = self.policy.is_allowed(self.product_id, host, ip)

        if not decision.allowed:
            await self.audit.log_block(
                self.product_id, host, ip, url_str, decision.reason
            )
            emit_egress_blocked_signal(
                product_id=self.product_id,
                host=host,
                ip=ip,
                reason=decision.reason,
            )
            raise EgressBlocked(
                product_id=self.product_id,
                host=host,
                ip=ip,
                reason=decision.reason,
            )

        await self.audit.log_allow(
            self.product_id, host, ip, url_str, decision.reason
        )
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()


class EgressGate:
    """Factory for gate-enforced httpx.AsyncClient instances.

    Usage::

        gate = EgressGate(policy, audit)
        async with gate.get_client() as client:
            resp = await client.get("https://api.sendgrid.com/v3/mail/send")
    """

    def __init__(
        self,
        policy: EgressPolicy | None = None,
        audit: EgressAuditLog | None = None,
        resolve_fn: DNSResolver | None = None,
    ) -> None:
        self._policy = policy or get_egress_policy()
        self._audit = audit or get_egress_audit()
        self._resolve_fn = resolve_fn

    def get_client(self, product_id: str | None = None, **kwargs: Any) -> httpx.AsyncClient:
        """Return a gate-enforced AsyncClient.

        If product_id is None, reads it from the current ProductContext.
        Raises RuntimeError if neither is available.
        """
        if product_id is None:
            ctx = get_product_context_or_none()
            if ctx is None:
                raise RuntimeError(
                    "EgressGate.get_client() called without product_id and no "
                    "ProductContext is set. Pass product_id explicitly or set context."
                )
            product_id = ctx.product_id

        transport = EgressGateTransport(
            product_id=product_id,
            policy=self._policy,
            audit=self._audit,
            resolve_fn=self._resolve_fn,
        )
        return httpx.AsyncClient(transport=transport, **kwargs)


_default_gate: EgressGate | None = None


def get_egress_gate() -> EgressGate:
    global _default_gate
    if _default_gate is None:
        _default_gate = EgressGate()
    return _default_gate


def reset_egress_gate() -> None:
    global _default_gate
    _default_gate = None
