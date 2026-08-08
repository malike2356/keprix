"""Invoke engine: grant, pack, schema, Soft Wall, budget, no free tool executor."""

from __future__ import annotations

import time
from typing import Any

from keprix.product_sidecar.auth import get_token_service
from keprix.product_sidecar.handlers import HANDLERS
from keprix.product_sidecar.registry import get_product_pack_registry
from keprix.product_sidecar.state import get_circuit, get_kill_switches
from keprix.product_sidecar.types import ErrorCode, NodeStatus, RequestContext, RiskClass


class InvokeError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 403, extra: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.extra = extra or {}

    def as_dict(self) -> dict[str, Any]:
        return {"error": self.message, "code": self.code, **self.extra}


async def invoke_node(
    ctx: RequestContext,
    *,
    node_key: str,
    input_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    payload = dict(input_payload or {})
    registry = get_product_pack_registry()
    kills = get_kill_switches()
    circuit = get_circuit()

    if kills.force_carina and node_key.startswith("agent."):
        raise InvokeError(ErrorCode.DENIED.value, "force_carina kill switch active", http_status=503)

    if not circuit.allow():
        raise InvokeError(ErrorCode.CIRCUIT_OPEN.value, "circuit open; use product fallback", http_status=503)

    try:
        pack = registry.require(ctx.product)
    except KeyError as exc:
        raise InvokeError(ErrorCode.DENIED.value, f"unknown product {ctx.product}") from exc

    if not pack.enabled:
        raise InvokeError(ErrorCode.PACK_DISABLED.value, "pack disabled", http_status=503)

    if registry.is_node_disabled(ctx.product, node_key):
        raise InvokeError(ErrorCode.DENIED.value, "node kill switch", http_status=403)

    node = pack.nodes.get(node_key)
    if node is None:
        raise InvokeError(ErrorCode.UNKNOWN_NODE.value, f"unknown node {node_key}", http_status=404)

    # Cross-product: never compose Clinicom/Petraclus from carina pack
    if node.product not in {ctx.product, "carina"} and pack.wrapper_of != "carina":
        raise InvokeError(ErrorCode.CROSS_PRODUCT.value, "cross-product composition denied")

    if node.status == NodeStatus.NOT_CONFIGURED:
        return {
            "error": "not_configured",
            "code": ErrorCode.NOT_CONFIGURED.value,
            "node": node_key,
            "guidance": node.operator_guidance,
        }

    if node.status == NodeStatus.DISABLED:
        raise InvokeError(ErrorCode.DENIED.value, "node disabled")

    tokens = get_token_service()
    if not tokens.has_grant(ctx, node.required_grants):
        tokens._audit_event(  # noqa: SLF001 - intentional audit
            "deny_missing_grant",
            product=ctx.product,
            workspace_id=ctx.workspace_id,
            node=node_key,
        )
        raise InvokeError(ErrorCode.DENIED.value, "missing grant", extra={"node": node_key})

    if ctx.product == "aiva" and (node.carina_admin_only or not node.aiva_sku_ok):
        raise InvokeError(ErrorCode.DENIED.value, "aiva sku cannot call this node")

    if ctx.workspace_id and not kills.consume_budget(ctx.workspace_id, node_key, node.budget_units):
        raise InvokeError(ErrorCode.BUDGET_EXCEEDED.value, "budget exceeded", http_status=429)

    # Fill workspace from payload when compat token left it blank
    if not ctx.workspace_id:
        ctx.workspace_id = str(payload.get("workspace_id") or "").strip()
    if not ctx.workspace_id:
        raise InvokeError(ErrorCode.VALIDATION.value, "workspace_id required", http_status=422)

    if ctx.shadow and node.risk in {
        RiskClass.OUTBOUND,
        RiskClass.DESTRUCTIVE,
        RiskClass.HIGH_RISK,
    }:
        return {
            "error": "soft_wall_required",
            "code": ErrorCode.SOFT_WALL_REQUIRED.value,
            "shadow_blocked": True,
            "node": node_key,
        }
    if ctx.shadow and node.risk == RiskClass.MUTATE and node_key not in {
        "agent.run",
        "agent.interrupt",
        "memory.put",
        "jobs.cancel",
    }:
        return {
            "error": "soft_wall_required",
            "code": ErrorCode.SOFT_WALL_REQUIRED.value,
            "shadow_blocked": True,
            "node": node_key,
        }

    handler_product = registry.resolve_handler_product(ctx.product)
    # Handlers are shared carina implementations
    handler = HANDLERS.get(node_key)
    if handler is None:
        raise InvokeError(ErrorCode.UNKNOWN_NODE.value, f"no handler for {node_key}", http_status=501)

    # Ensure handler context product family is carina for shared impl
    exec_ctx = RequestContext(
        product=ctx.product,
        deployment=ctx.deployment,
        workspace_id=ctx.workspace_id,
        actor_id=ctx.actor_id,
        grants=ctx.grants,
        purpose=ctx.purpose,
        correlation_id=ctx.correlation_id,
        session_id=ctx.session_id or str(payload.get("session_id") or ""),
        roles=ctx.roles,
        entitlements=ctx.entitlements,
        shadow=ctx.shadow,
        engine_mode=ctx.engine_mode,
        audience=ctx.audience,
        token_mode=ctx.token_mode,
    )

    try:
        result = await handler(exec_ctx, payload)
        circuit.record_success()
    except Exception as exc:
        circuit.record_failure()
        raise InvokeError("handler_error", str(exc)[:300], http_status=502) from exc

    latency_ms = (time.perf_counter() - started) * 1000
    if isinstance(result, dict) and result.get("code") == ErrorCode.SOFT_WALL_REQUIRED.value:
        return {
            **result,
            "node": node_key,
            "correlation_id": ctx.correlation_id,
            "latency_ms": latency_ms,
            "handler_product": handler_product,
        }

    return {
        "ok": True,
        "node": node_key,
        "product": ctx.product,
        "handler_product": handler_product,
        "workspace_id": ctx.workspace_id,
        "correlation_id": ctx.correlation_id,
        "latency_ms": latency_ms,
        "result": result,
        "token_mode": ctx.token_mode,
    }
