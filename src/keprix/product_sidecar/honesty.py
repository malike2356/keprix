"""Fail-closed capability honesty for product sidecar packs.

A node may be labelled ``live`` or ``approval_required`` only when all of:
- an executable handler is registered
- a permitted connector route exists for the required HTTP method
- at least one behavioral test is registered for the node

``proposal_only`` and ``intentionally_forbidden`` are preserved as explicit
classifications. Otherwise status is ``not_configured`` (no handler) or
``degraded`` (handler present but route/test incomplete). Declared
``disabled`` is preserved.
"""

from __future__ import annotations

from typing import Any, Iterable

from keprix.product_sidecar.types import CapabilityNode, NodeStatus

# Pack nodes with FakeProductConnector conformance tests (prompts 639-640).
# Populated by propreneur_ops.EXECUTABLE_HTTP_NODES at import time via register.
BEHAVIORAL_TEST_NODES: frozenset[str] = frozenset()


def set_behavioral_test_nodes(nodes: Iterable[str]) -> None:
    global BEHAVIORAL_TEST_NODES
    BEHAVIORAL_TEST_NODES = frozenset(nodes)


def _load_node_connector_routes() -> dict[str, tuple[str, str]]:
    try:
        from keprix.product_sidecar.generated import load_propreneur_pack_nodes
    except Exception:
        return {}
    out: dict[str, tuple[str, str]] = {}
    for item in load_propreneur_pack_nodes().get("nodes") or []:
        method = str(item.get("http_method") or "").upper()
        path = str(item.get("http_path") or "")
        key = str(item.get("key") or "")
        if key and method and path:
            out[key] = (method, path)
    return out


NODE_CONNECTOR_ROUTES: dict[str, tuple[str, str]] = _load_node_connector_routes()


def refresh_connector_routes() -> None:
    global NODE_CONNECTOR_ROUTES
    NODE_CONNECTOR_ROUTES = _load_node_connector_routes()


def _route_permitted(
    connector: dict[str, Any] | None,
    *,
    method: str,
    path: str,
) -> bool:
    routes = list((connector or {}).get("routes") or [])
    method_u = method.upper()
    for route in routes:
        if str(route.get("method") or "").upper() != method_u:
            continue
        if str(route.get("path") or "") == path:
            return True
    return False


def has_executable_handler(node_key: str) -> bool:
    # Lazy import: honesty must not import handlers at module load (handlers
    # registers propreneur ops which calls back into honesty).
    from keprix.product_sidecar.handlers import HANDLERS

    return node_key in HANDLERS and HANDLERS[node_key] is not None


def has_behavioral_test(node_key: str) -> bool:
    return node_key in BEHAVIORAL_TEST_NODES


def connector_route_ok(node_key: str, connector: dict[str, Any] | None) -> bool:
    required = NODE_CONNECTOR_ROUTES.get(node_key)
    if required is None:
        return False
    method, path = required
    return _route_permitted(connector, method=method, path=path)


_PRESERVED = frozenset(
    {
        NodeStatus.DISABLED,
        NodeStatus.INTENTIONALLY_FORBIDDEN,
        NodeStatus.PROPOSAL_ONLY,
    }
)


def resolve_fail_closed_status(
    node_key: str,
    declared: NodeStatus,
    *,
    connector: dict[str, Any] | None = None,
) -> NodeStatus:
    """Downgrade advertised status so health never lies about executability."""
    if declared in _PRESERVED:
        return declared

    if not has_executable_handler(node_key):
        return NodeStatus.NOT_CONFIGURED

    route_ok = connector_route_ok(node_key, connector)
    test_ok = has_behavioral_test(node_key)
    if not route_ok or not test_ok:
        return NodeStatus.DEGRADED

    if declared == NodeStatus.APPROVAL_REQUIRED:
        return NodeStatus.APPROVAL_REQUIRED
    return NodeStatus.LIVE


def apply_fail_closed_statuses(
    nodes: dict[str, CapabilityNode],
    *,
    connector: dict[str, Any] | None = None,
) -> dict[str, CapabilityNode]:
    """Return a new node map with fail-closed statuses applied."""
    out: dict[str, CapabilityNode] = {}
    for key, node in nodes.items():
        status = resolve_fail_closed_status(key, node.status, connector=connector)
        if status == node.status:
            out[key] = node
            continue
        guidance = node.operator_guidance
        if status == NodeStatus.NOT_CONFIGURED:
            note = (
                "Fail-closed: no executable product-sidecar handler; "
                "do not advertise as live (CRUD remediation in progress)."
            )
            guidance = f"{guidance} {note}".strip() if guidance else note
        elif status == NodeStatus.DEGRADED:
            note = (
                "Fail-closed: handler present but connector route and/or "
                "behavioral test incomplete; status degraded until remediation."
            )
            guidance = f"{guidance} {note}".strip() if guidance else note
        elif status in {NodeStatus.LIVE, NodeStatus.APPROVAL_REQUIRED} and node.status not in {
            NodeStatus.LIVE,
            NodeStatus.APPROVAL_REQUIRED,
        }:
            note = (
                "Executable: handler, permitted connector route, and "
                "behavioral test are present."
            )
            guidance = f"{guidance} {note}".strip() if guidance else note
        out[key] = CapabilityNode(
            key=node.key,
            version=node.version,
            title=node.title,
            product=node.product,
            domain=node.domain,
            risk=node.risk,
            status=status,
            required_grants=node.required_grants,
            entitlements=node.entitlements,
            soft_wall=node.soft_wall,
            sync=node.sync,
            input_schema=dict(node.input_schema),
            output_schema=dict(node.output_schema),
            timeout_seconds=node.timeout_seconds,
            budget_units=node.budget_units,
            idempotent=node.idempotent,
            operator_guidance=guidance,
            aiva_sku_ok=node.aiva_sku_ok,
            carina_admin_only=node.carina_admin_only,
        )
    return out


def assert_live_nodes_honest(
    nodes: Iterable[CapabilityNode],
    *,
    connector: dict[str, Any] | None = None,
) -> list[str]:
    """Return violation messages for executable nodes without prerequisites."""
    violations: list[str] = []
    for node in nodes:
        if node.status not in {NodeStatus.LIVE, NodeStatus.APPROVAL_REQUIRED}:
            continue
        if not has_executable_handler(node.key):
            violations.append(f"{node.key}: {node.status.value} without executable handler")
            continue
        if not connector_route_ok(node.key, connector):
            violations.append(f"{node.key}: {node.status.value} without permitted connector route")
        if not has_behavioral_test(node.key):
            violations.append(f"{node.key}: {node.status.value} without behavioral test")
    return violations
