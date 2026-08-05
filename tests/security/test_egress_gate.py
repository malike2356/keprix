"""Tests for security/egress_gate.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from keprix.security.egress_audit import EgressAuditLog
from keprix.security.egress_gate import EgressBlocked, EgressGate, EgressGateTransport
from keprix.security.egress_policy import EgressDecision, EgressPolicy


def _make_policy(allowed: bool, reason: str) -> EgressPolicy:
    policy = MagicMock(spec=EgressPolicy)
    policy.is_allowed.return_value = EgressDecision(allowed=allowed, reason=reason)
    return policy


def _make_audit() -> EgressAuditLog:
    audit = MagicMock(spec=EgressAuditLog)
    audit.log_allow = AsyncMock()
    audit.log_block = AsyncMock()
    return audit


def _make_inner(response: httpx.Response | None = None) -> httpx.AsyncBaseTransport:
    inner = MagicMock(spec=httpx.AsyncBaseTransport)
    inner.handle_async_request = AsyncMock(
        return_value=response or httpx.Response(200, content=b"ok")
    )
    inner.aclose = AsyncMock()
    return inner


def _build_transport(
    product_id="aiva",
    allowed=True,
    reason="host_in_allowlist",
    resolve_ip="54.1.1.1",
):
    policy = _make_policy(allowed, reason)
    audit = _make_audit()
    inner = _make_inner()

    async def fake_resolve(host: str) -> str:
        return resolve_ip

    transport = EgressGateTransport(
        product_id=product_id,
        policy=policy,
        audit=audit,
        resolve_fn=fake_resolve,
        inner=inner,
    )
    return transport, policy, audit, inner


@pytest.mark.asyncio
async def test_allowed_request_forwards():
    transport, policy, audit, inner = _build_transport(allowed=True)
    request = httpx.Request("GET", "https://api.sendgrid.com/v3/stats")
    response = await transport.handle_async_request(request)
    assert response.status_code == 200
    inner.handle_async_request.assert_called_once()


@pytest.mark.asyncio
async def test_allowed_request_logs_allow():
    transport, policy, audit, inner = _build_transport(allowed=True, reason="host_in_allowlist")
    request = httpx.Request("GET", "https://api.sendgrid.com/v3/stats")
    await transport.handle_async_request(request)
    audit.log_allow.assert_called_once()
    call_args = audit.log_allow.call_args[0]
    assert call_args[0] == "aiva"
    assert call_args[1] == "api.sendgrid.com"


@pytest.mark.asyncio
async def test_blocked_request_raises_egress_blocked():
    transport, policy, audit, inner = _build_transport(
        allowed=False, reason="private_ip_blocked", resolve_ip="192.168.1.1"
    )
    request = httpx.Request("GET", "https://internal.service/api")
    with pytest.raises(EgressBlocked) as exc_info:
        await transport.handle_async_request(request)
    assert exc_info.value.product_id == "aiva"
    assert "192.168.1.1" in str(exc_info.value)
    assert "private_ip_blocked" in exc_info.value.reason


@pytest.mark.asyncio
async def test_blocked_request_logs_block():
    transport, policy, audit, inner = _build_transport(
        allowed=False, reason="host_not_in_allowlist"
    )
    request = httpx.Request("GET", "https://evil.com/data")
    with pytest.raises(EgressBlocked):
        await transport.handle_async_request(request)
    audit.log_block.assert_called_once()
    assert audit.log_allow.call_count == 0


@pytest.mark.asyncio
async def test_blocked_request_does_not_forward():
    transport, policy, audit, inner = _build_transport(allowed=False, reason="host_denied_by_policy")
    request = httpx.Request("GET", "https://api.abbis.com/data")
    with pytest.raises(EgressBlocked):
        await transport.handle_async_request(request)
    inner.handle_async_request.assert_not_called()


@pytest.mark.asyncio
async def test_dns_cache_reuses_resolution():
    resolve_calls = []

    async def counting_resolve(host: str) -> str:
        resolve_calls.append(host)
        return "54.1.1.1"

    policy = _make_policy(True, "host_in_allowlist")
    audit = _make_audit()
    inner = _make_inner()

    transport = EgressGateTransport(
        product_id="aiva",
        policy=policy,
        audit=audit,
        resolve_fn=counting_resolve,
        inner=inner,
    )

    for _ in range(3):
        request = httpx.Request("GET", "https://api.sendgrid.com/v3/stats")
        await transport.handle_async_request(request)

    # DNS should have been called only once (cached after first call)
    assert resolve_calls.count("api.sendgrid.com") == 1


@pytest.mark.asyncio
async def test_egress_gate_get_client_with_product_id():
    policy = _make_policy(True, "host_in_allowlist")
    audit = _make_audit()
    gate = EgressGate(policy=policy, audit=audit)
    client = gate.get_client(product_id="aiva")
    assert isinstance(client, httpx.AsyncClient)
    await client.aclose()


def test_egress_blocked_str():
    exc = EgressBlocked("aiva", "192.168.1.1", "192.168.1.1", "private_ip_blocked")
    assert "private_ip_blocked" in str(exc)
    assert "aiva" in str(exc)
    assert "192.168.1.1" in str(exc)
