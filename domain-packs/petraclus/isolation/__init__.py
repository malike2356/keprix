"""Six-layer IsolationEnforcer for Petraclus sidecar requests."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from nodes.catalog import FORBIDDEN_NODES, MUTATE_RISKS, all_nodes, edition_allows, is_action_node


class IsolationDenied(PermissionError):
    def __init__(self, layer: str, reason: str) -> None:
        self.layer = layer
        self.reason = reason
        super().__init__(f"{layer}:{reason}")


@dataclass
class TargetGrant:
    workspace_id: str
    target_type: str
    target_value: str
    resolved_addresses: list[str] = field(default_factory=list)
    ports: list[int] = field(default_factory=list)
    protocols: list[str] = field(default_factory=list)
    allowed_techniques: list[str] = field(default_factory=list)
    excluded_ranges: list[str] = field(default_factory=list)
    window_start: str = ""
    window_end: str = ""
    owner_evidence: str = ""
    approver: str = ""
    expiry: str = ""
    revoked: bool = False
    grant_id: str = ""
    allows_internal: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "workspace_id": self.workspace_id,
            "target_type": self.target_type,
            "target_value": self.target_value,
            "resolved_addresses": list(self.resolved_addresses),
            "ports": list(self.ports),
            "protocols": list(self.protocols),
            "allowed_techniques": list(self.allowed_techniques),
            "excluded_ranges": list(self.excluded_ranges),
            "window_start": self.window_start,
            "window_end": self.window_end,
            "owner_evidence": self.owner_evidence,
            "approver": self.approver,
            "expiry": self.expiry,
            "revoked": self.revoked,
            "allows_internal": self.allows_internal,
        }


@dataclass
class IsolationContext:
    product: str = "petraclus"
    workspace_id: str = ""
    tenant_id: str = ""
    edition: str = "community"
    role: str = "analyst"
    grants: frozenset[str] = field(default_factory=frozenset)
    purpose: str = ""
    actor_id: str = ""
    target_grant: TargetGrant | None = None


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_blocked_internal_ip(value: str) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    if text in {"localhost", "metadata.google.internal"}:
        return True
    if text.endswith(".local") or text.endswith(".internal"):
        return True
    try:
        ip = ipaddress.ip_address(text.split("%")[0])
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or str(ip) in {"169.254.169.254", "0.0.0.0"}
    )


class IsolationEnforcer:
    """Fail-closed isolation: product, workspace, edition, role/grants, target grant, purpose."""

    LAYERS = (
        "product",
        "workspace_tenant",
        "edition",
        "role_grants",
        "target_grant",
        "purpose",
    )

    def assert_product(self, ctx: IsolationContext) -> None:
        if ctx.product != "petraclus":
            raise IsolationDenied("product", "wrong_product")

    def assert_workspace(self, ctx: IsolationContext, record_workspace: str | None = None) -> None:
        if not ctx.workspace_id:
            raise IsolationDenied("workspace_tenant", "missing_workspace")
        if record_workspace and record_workspace != ctx.workspace_id:
            raise IsolationDenied("workspace_tenant", "cross_workspace")

    def assert_edition(self, ctx: IsolationContext, node_key: str) -> None:
        node = all_nodes().get(node_key) or {}
        edition_min = str(node.get("edition_min") or "community")
        if not edition_allows(ctx.edition, edition_min):
            raise IsolationDenied("edition", f"requires:{edition_min}")

    def assert_role_grants(self, ctx: IsolationContext, node_key: str) -> None:
        if node_key in FORBIDDEN_NODES:
            raise IsolationDenied("role_grants", f"forbidden_node:{node_key}")
        grants = ctx.grants
        if is_action_node(node_key) and "mutate" not in grants:
            raise IsolationDenied("role_grants", "read_only_cannot_mutate")
        if "node:*" in grants or "*" in grants:
            return
        need = f"node:{node_key}"
        if need not in grants and node_key not in grants:
            raise IsolationDenied("role_grants", f"grant_missing:{need}")

    def revalidate_target_grant(self, grant: TargetGrant | None) -> TargetGrant:
        if grant is None:
            raise IsolationDenied("target_grant", "missing_grant")
        if grant.revoked:
            raise IsolationDenied("target_grant", "revoked")
        expiry = _parse_iso(grant.expiry)
        if expiry is not None and expiry < datetime.now(timezone.utc):
            raise IsolationDenied("target_grant", "expired")
        if "*" in grant.target_value or grant.target_value.endswith("/*") or grant.target_type == "wildcard":
            raise IsolationDenied("target_grant", "wildcard_denied")
        for addr in [grant.target_value, *list(grant.resolved_addresses)]:
            if is_blocked_internal_ip(addr) and not grant.allows_internal:
                raise IsolationDenied("target_grant", "internal_ip_denied")
            if is_blocked_internal_ip(addr) and grant.allows_internal:
                # Explicit naming required: internal value must appear on the grant
                if addr != grant.target_value and addr not in grant.resolved_addresses:
                    raise IsolationDenied("target_grant", "internal_ip_denied")
        return grant

    def assert_target_for_action(
        self,
        ctx: IsolationContext,
        *,
        node_key: str,
        grant: TargetGrant | None = None,
    ) -> TargetGrant | None:
        node = all_nodes().get(node_key) or {}
        needs_grant = bool(node.get("requires_target_grant")) or node.get("risk") in {
            "active_scan",
            "credentialed_scan",
        }
        if not needs_grant:
            return grant or ctx.target_grant
        active = grant or ctx.target_grant
        validated = self.revalidate_target_grant(active)
        if validated.workspace_id != ctx.workspace_id:
            raise IsolationDenied("target_grant", "grant_workspace_mismatch")
        return validated

    def assert_purpose(self, ctx: IsolationContext, node_key: str) -> None:
        if not ctx.purpose:
            raise IsolationDenied("purpose", "missing_purpose")
        node = all_nodes().get(node_key) or {}
        if node.get("risk") in MUTATE_RISKS and ctx.purpose in {"browse", "read_only"}:
            raise IsolationDenied("purpose", "purpose_blocks_mutate")

    def enforce(
        self,
        ctx: IsolationContext,
        *,
        node_key: str,
        record_workspace: str | None = None,
        require_target: bool | None = None,
        grant: TargetGrant | None = None,
    ) -> dict[str, Any]:
        self.assert_product(ctx)
        self.assert_workspace(ctx, record_workspace)
        self.assert_edition(ctx, node_key)
        self.assert_role_grants(ctx, node_key)
        node = all_nodes().get(node_key) or {}
        needs = require_target if require_target is not None else bool(node.get("requires_target_grant"))
        if needs or node.get("risk") in {"active_scan", "credentialed_scan"}:
            self.assert_target_for_action(ctx, node_key=node_key, grant=grant)
        self.assert_purpose(ctx, node_key)
        return {
            "ok": True,
            "isolation_version": "petraclus-pts-00@1.0.0",
            "layers": list(self.LAYERS),
            "workspace_id": ctx.workspace_id,
            "edition": ctx.edition,
            "node_key": node_key,
        }
