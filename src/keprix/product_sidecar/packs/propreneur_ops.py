"""Propreneur pack operation adapter (prompts 639-640).

Both ``/v1/products/propreneur/invoke`` and the Keprix-backed chat tool loop
call ``execute_propreneur_node`` so results share one envelope. Handlers use the
typed ProductApiConnector against Propreneur's versioned API; they never write
Keprix local CRM as a substitute for Propreneur records.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Awaitable, Callable

from keprix.product_sidecar.connector import (
    ConnectorDenied,
    ProductApiConnector,
    connector_from_pack,
    declared_path_params,
    substitute_path,
)
from keprix.product_sidecar.generated import load_propreneur_pack_nodes
from keprix.product_sidecar.trusted_context import (
    TrustedExecutionContext,
    strip_identity_from_model_args,
)
from keprix.product_sidecar.types import RequestContext

logger = logging.getLogger(__name__)

Handler = Callable[[RequestContext, dict[str, Any]], Awaitable[dict[str, Any]]]

# Path-param aliases accepted from model/chat payloads.
_ID_ALIASES: dict[str, tuple[str, ...]] = {
    "propertyId": ("property_id", "id"),
    "contactId": ("contact_id", "owner_id", "id"),
    "tenancyId": ("tenancy_id", "id"),
    "dealId": ("deal_id", "id"),
    "ticketId": ("ticket_id", "maintenance_id", "id"),
    "projectId": ("project_id", "id"),
    "leadId": ("lead_id", "sourcing_id", "id"),
    "documentId": ("document_id", "id"),
    "expenseId": ("expense_id", "id"),
    "appointmentId": ("appointment_id", "id"),
}


def _catalog_nodes() -> list[dict[str, Any]]:
    return list(load_propreneur_pack_nodes().get("nodes") or [])


def _http_nodes() -> frozenset[str]:
    return frozenset(
        str(n["key"])
        for n in _catalog_nodes()
        if str(n.get("http_method") or "") and str(n.get("http_path") or "")
    )


EXECUTABLE_HTTP_NODES: frozenset[str] = _http_nodes()

# Back-compat alias used by older tests.
LIVE_PROPERTY_NODES = frozenset(
    {"property_get", "property_create", "property_update", "property_archive"}
)


def _build_tool_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    action_suffixes = ("_get", "_create", "_update", "_archive", "_search", "_cancel", "_propose")
    for key in sorted(EXECUTABLE_HTTP_NODES):
        aliases[key] = key
        for suffix in action_suffixes:
            if key.endswith(suffix):
                action = suffix[1:]
                rest = key[: -len(suffix)]
                aliases[f"{action}_{rest}"] = key
                break
        op = next((n.get("operation_id") for n in _catalog_nodes() if n.get("key") == key), None)
        if op:
            aliases[str(op)] = key
    # Historical bridge / chat names
    aliases.update(
        {
            "propreneur-get-property": "property_get",
            "propreneur-get-portfolio": "ask_portfolio",
            "propreneur-get-contacts": "contact_search",
            "propreneur-get-deals": "deal_search",
            "propreneur-get-maintenance-requests": "maintenance_search",
            "propreneur-get-expenses": "expense_search",
        }
    )
    return aliases


TOOL_NAME_TO_NODE: dict[str, str] = _build_tool_aliases()


def resolve_pack_node(name: str) -> str | None:
    key = str(name or "").strip()
    return TOOL_NAME_TO_NODE.get(key)


def _node_catalog_entry(node_key: str) -> dict[str, Any]:
    for item in _catalog_nodes():
        if str(item.get("key") or "") == node_key:
            return dict(item)
    raise KeyError(f"unknown propreneur pack node: {node_key}")


def trusted_from_request_context(
    ctx: RequestContext,
    payload: dict[str, Any] | None = None,
) -> TrustedExecutionContext:
    raw = dict(payload or {})
    actor_type = str(raw.get("actor_type") or ("platform_user" if ctx.product == "platform" else "tenant_user"))
    return TrustedExecutionContext(
        product=ctx.product or "propreneur",
        workspace_id=ctx.workspace_id,
        actor_id=ctx.actor_id,
        actor_type=actor_type,
        conversation_id=str(raw.get("conversation_id") or ctx.session_id or ""),
        worker_id=str(raw.get("worker_id") or ""),
        correlation_id=ctx.correlation_id,
        granted_scopes=tuple(sorted(ctx.grants)),
        channel_binding=str(raw.get("channel_binding") or ""),
        approval_evidence=str(raw.get("approval_token") or raw.get("approval_id") or ""),
        idempotency_key=str(raw.get("idempotency_key") or ""),
        if_match=str(raw.get("if_match") or raw.get("etag") or "").strip(),
        platform_user_id=str(raw.get("platform_user_id") or ""),
        platform_conversation_id=str(raw.get("platform_conversation_id") or ""),
        platform_scope=bool(raw.get("platform_scope")),
    )


def _split_path_and_body(
    method: str,
    path_template: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    declared = set(declared_path_params(path_template))
    params: dict[str, Any] = {}
    body = strip_identity_from_model_args(payload)
    for path_key, alts in _ID_ALIASES.items():
        if path_key in declared and path_key not in body:
            for alt in alts:
                if alt in body:
                    body[path_key] = body.pop(alt)
                    break
    for key in list(declared):
        if key in body:
            params[key] = body.pop(key)
    if method.upper() == "GET":
        return params, None
    return params, body


def _envelope(
    *,
    success: bool,
    status: str,
    correlation_id: str,
    data: Any = None,
    error: dict[str, Any] | None = None,
    approval: dict[str, Any] | None = None,
    idempotency: dict[str, Any] | None = None,
    audit_reference: str | None = None,
    retry: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "success": success,
        "data": data,
        "error": error,
        "status": status,
        "correlation_id": correlation_id,
        "idempotency": idempotency,
        "approval": approval,
        "audit_reference": audit_reference,
        "retry": retry,
    }
    if extra:
        out.update(extra)
    return out


async def execute_propreneur_node(
    ctx: RequestContext,
    node_key: str,
    payload: dict[str, Any] | None = None,
    *,
    connector: ProductApiConnector | None = None,
    trusted: TrustedExecutionContext | None = None,
) -> dict[str, Any]:
    """Shared adapter for pack invoke and chat tool routing."""
    from keprix.product_sidecar.control_plane import IdempotencyConflict, fingerprint_payload
    from keprix.product_sidecar.handlers import _require_soft_wall
    from keprix.product_sidecar.state import (
        get_approval_store,
        get_event_store,
        get_idempotency_ledger,
        get_receipt_store,
    )

    payload = dict(payload or {})
    entry = _node_catalog_entry(node_key)
    method = str(entry.get("http_method") or "").upper()
    path_template = str(entry.get("http_path") or "")
    if not method or not path_template:
        declared = str(entry.get("status") or "not_configured")
        status = "proposal_only" if declared == "proposal_only" else "not_configured"
        return _envelope(
            success=False,
            status=status,
            correlation_id=ctx.correlation_id,
            error={
                "code": status,
                "message": f"{node_key} has no HTTP binding",
                "retryable": False,
            },
            retry={
                "safe": False,
                "guidance": "Use Soft Wall proposal flow or wait for a typed Aiva route.",
            },
            extra={"node": node_key},
        )

    trusted_ctx = trusted or trusted_from_request_context(ctx, payload)

    if bool(entry.get("soft_wall")):
        blocked = await _require_soft_wall(ctx, payload, node_key)
        if blocked:
            return _envelope(
                success=False,
                status="awaiting_approval",
                correlation_id=ctx.correlation_id,
                error={
                    "code": "soft_wall_required",
                    "message": str(blocked.get("reason") or "approval required"),
                    "retryable": True,
                },
                approval={
                    "state": "pending",
                    "approval_id": blocked.get("approval_id"),
                    "digest": blocked.get("input_hash"),
                    "deep_link": blocked.get("deep_link"),
                },
                retry={
                    "safe": True,
                    "guidance": "Resume with matching approval_id after Soft Wall approval.",
                },
                extra={
                    "code": "soft_wall_required",
                    "approval_id": blocked.get("approval_id"),
                    "deep_link": blocked.get("deep_link"),
                    "input_hash": blocked.get("input_hash"),
                    "node": node_key,
                },
            )

    path_params, body = _split_path_and_body(method, path_template, payload)
    try:
        resolved_path = substitute_path(path_template, path_params)
    except ConnectorDenied as exc:
        return _envelope(
            success=False,
            status="failed",
            correlation_id=ctx.correlation_id,
            error={"code": "validation", "message": str(exc), "retryable": False},
            retry={"safe": False, "guidance": "Provide required path parameters."},
            extra={"node": node_key},
        )

    headers = trusted_ctx.to_headers()
    if body is not None:
        body = strip_identity_from_model_args(body)

    idem_key = trusted_ctx.idempotency_key or str(payload.get("idempotency_key") or "")
    idem_hash = fingerprint_payload(
        {
            "node": node_key,
            "method": method,
            "path": path_template,
            "path_params": path_params,
            "body": body or {},
        }
    )
    ledger = get_idempotency_ledger()
    ledger_key = ""
    try:
        claim = ledger.begin(
            product=ctx.product or "propreneur",
            workspace_id=ctx.workspace_id,
            actor_id=ctx.actor_id,
            operation=str(entry.get("operation_id") or node_key),
            idempotency_key=idem_key,
            input_hash=idem_hash,
        )
    except IdempotencyConflict as exc:
        return _envelope(
            success=False,
            status="conflict",
            correlation_id=ctx.correlation_id,
            error={
                "code": "idempotency_fingerprint_mismatch",
                "message": str(exc),
                "retryable": False,
            },
            data=exc.current.get("result"),
            retry=exc.current.get("retry"),
            extra={"node": node_key, "idempotency": exc.current},
        )
    if claim.get("state") == "replay":
        replayed = dict(claim.get("result") or {})
        replayed["idempotency"] = {"key": idem_key, "state": "replay"}
        return replayed
    ledger_key = str(claim.get("ledger_key") or "")

    client = connector or connector_from_pack("propreneur")
    try:
        raw = await client.call_manifest(
            method=method,
            path_template=path_template,
            path_params=path_params,
            json_body=body,
            headers=headers,
            idempotency_key=idem_key,
        )
    except ConnectorDenied as exc:
        code = str(exc)
        if "version_conflict" in code or "409" in code:
            return _envelope(
                success=False,
                status="conflict",
                correlation_id=ctx.correlation_id,
                error={
                    "code": "version_conflict",
                    "message": code,
                    "retryable": True,
                    "etag": headers.get("If-Match"),
                },
                retry={
                    "safe": True,
                    "guidance": "GET the current record, refresh If-Match/etag, then retry with a new idempotency key if the body changed.",
                },
                extra={"node": node_key, "method": method, "path": resolved_path},
            )
        return _envelope(
            success=False,
            status="failed",
            correlation_id=ctx.correlation_id,
            error={"code": "connector_denied", "message": code, "retryable": "circuit_open" in code},
            retry={
                "safe": "circuit_open" not in code,
                "guidance": "Check connector allowlist, circuit, and path parameters.",
            },
            extra={"node": node_key, "method": method, "path": resolved_path},
        )
    except Exception as exc:
        logger.exception("propreneur connector error for %s", node_key)
        return _envelope(
            success=False,
            status="failed",
            correlation_id=ctx.correlation_id,
            error={"code": "upstream_error", "message": str(exc)[:300], "retryable": True},
            retry={
                "safe": True,
                "guidance": "Retry with the same idempotency key if the mutation is uncertain.",
            },
            extra={"node": node_key},
        )

    record_id = ""
    result_data: Any = raw
    if isinstance(raw, dict):
        nested = raw.get("data")
        if isinstance(nested, dict):
            result_data = nested
            if nested.get("id") is not None:
                record_id = str(nested.get("id"))
        elif isinstance(nested, list):
            result_data = nested
        elif raw.get("id") is not None:
            record_id = str(raw.get("id"))
        elif raw.get("record_id") is not None:
            record_id = str(raw.get("record_id"))
        elif path_params:
            record_id = str(next(iter(path_params.values())))
    elif path_params:
        record_id = str(next(iter(path_params.values())))

    response_etag = ""
    if hasattr(client, "last_response_headers"):
        response_etag = str(getattr(client, "last_response_headers", {}).get("etag") or "")

    causation_id = f"keprix:{ctx.correlation_id or uuid_hex()}:{node_key}"
    if method != "GET":
        # Emit a local control-plane event so outbox echoes with this causation are suppressed.
        get_event_store().ingest(
            {
                "id": f"mut_{causation_id}",
                "type": f"propreneur.mutation.{node_key}",
                "source": "keprix",
                "product": ctx.product or "propreneur",
                "workspace_id": ctx.workspace_id,
                "deployment": ctx.deployment or "local",
                "causation_id": causation_id,
                "data": {"node": node_key, "record_id": record_id, "path": resolved_path},
                "sensitivity": "internal",
            }
        )

    receipt = get_receipt_store().record(
        product=ctx.product or "propreneur",
        workspace_id=ctx.workspace_id,
        node_key=node_key,
        status="completed",
        correlation_id=ctx.correlation_id,
        conversation_id=ctx.session_id or trusted_ctx.conversation_id,
        approval_id=str(payload.get("approval_id") or ""),
        record_id=record_id,
        audit_event_id=causation_id if method != "GET" else "",
        method=method,
        path=resolved_path,
        result_summary={"ok": True, "fixture": bool(isinstance(raw, dict) and raw.get("fixture"))},
    )
    if payload.get("approval_id"):
        get_approval_store().attach_receipt(str(payload["approval_id"]), receipt["receipt_id"])

    result = _envelope(
        success=True,
        status="completed",
        correlation_id=ctx.correlation_id,
        data=result_data,
        idempotency={"key": idem_key or None, "state": "fresh" if idem_key else "n/a"},
        audit_reference=receipt["receipt_id"],
        retry={
            "safe": method == "GET",
            "guidance": "GET is safe to retry; mutations need idempotency evidence.",
        },
        extra={
            "node": node_key,
            "operation_id": entry.get("operation_id"),
            "method": method,
            "path": resolved_path,
            "ok": True,
            "receipt_id": receipt["receipt_id"],
            "causation_id": causation_id if method != "GET" else None,
            "record_id": record_id or None,
            "etag": response_etag or None,
        },
    )
    if ledger_key:
        ledger.complete(ledger_key, result)
    return result


def uuid_hex() -> str:
    return uuid.uuid4().hex[:10]


def make_handler(node_key: str) -> Handler:
    async def _handler(ctx: RequestContext, payload: dict[str, Any]) -> dict[str, Any]:
        return await execute_propreneur_node(ctx, node_key, payload)

    _handler.__name__ = f"handle_{node_key}"
    _handler.__qualname__ = f"handle_{node_key}"
    return _handler


# Named property handlers kept for import stability (prompt 639 tests).
handle_property_get = make_handler("property_get")
handle_property_create = make_handler("property_create")
handle_property_update = make_handler("property_update")
handle_property_archive = make_handler("property_archive")


def register_propreneur_handlers(handlers: dict[str, Handler]) -> list[str]:
    """Register HTTP-backed pack nodes onto HANDLERS and return registered keys."""
    from keprix.product_sidecar.honesty import refresh_connector_routes, set_behavioral_test_nodes

    registered: list[str] = []
    for key in sorted(EXECUTABLE_HTTP_NODES):
        handlers[key] = make_handler(key)
        registered.append(key)
    set_behavioral_test_nodes(registered)
    refresh_connector_routes()
    return registered


def request_context_from_trusted(trusted: TrustedExecutionContext) -> RequestContext:
    return RequestContext(
        product=trusted.product or "propreneur",
        deployment="chat",
        workspace_id=trusted.workspace_id,
        actor_id=trusted.actor_id,
        grants=frozenset(trusted.granted_scopes or ("*",)),
        purpose="chat_tool",
        correlation_id=trusted.correlation_id or "",
        session_id=trusted.conversation_id,
        token_mode="trusted_callback",
    )
