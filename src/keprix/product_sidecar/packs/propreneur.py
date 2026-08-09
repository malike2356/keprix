"""Propreneur product pack node catalog for the shared product_sidecar registry.

Nodes are generated from the canonical agent capabilities contract (prompt 637).
Regenerate: bash keprix/scripts/regen-propreneur-agent-contract.sh
"""

from __future__ import annotations

from keprix.product_sidecar.generated import load_propreneur_pack_nodes
from keprix.product_sidecar.types import CapabilityNode, NodeStatus, RiskClass

_RISK = {
    "read": RiskClass.READ,
    "propose": RiskClass.PROPOSE,
    "mutate": RiskClass.MUTATE,
    "outbound": RiskClass.OUTBOUND,
    "destructive": RiskClass.DESTRUCTIVE,
    "high_risk": RiskClass.HIGH_RISK,
}

_STATUS = {
    "live": NodeStatus.LIVE,
    "approval_required": NodeStatus.APPROVAL_REQUIRED,
    "proposal_only": NodeStatus.PROPOSAL_ONLY,
    "intentionally_forbidden": NodeStatus.INTENTIONALLY_FORBIDDEN,
    "stub": NodeStatus.STUB,
    "not_configured": NodeStatus.NOT_CONFIGURED,
    "disabled": NodeStatus.DISABLED,
    "degraded": NodeStatus.DEGRADED,
}


def build_propreneur_nodes() -> dict[str, CapabilityNode]:
    catalog = load_propreneur_pack_nodes()
    nodes: dict[str, CapabilityNode] = {}
    for item in catalog.get("nodes") or []:
        key = str(item["key"])
        risk = str(item.get("risk") or "read")
        status = str(item.get("status") or "not_configured")
        soft_wall = bool(item.get("soft_wall"))
        nodes[key] = CapabilityNode(
            key=key,
            version="1.0.0",
            title=str(item.get("title") or key),
            product="propreneur",
            domain=str(item.get("domain") or "general"),
            risk=_RISK[risk],
            status=_STATUS.get(status, NodeStatus.NOT_CONFIGURED),
            required_grants=tuple(item.get("required_grants") or (f"node:{key}",)),
            entitlements=("propreneur",),
            soft_wall=soft_wall,
            sync=True,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            idempotent=bool(item.get("idempotent")),
            operator_guidance=(
                "UK property MIS pack; Propreneur remains authorization and data authority. "
                "Mutate, destructive, and propose nodes require soft-wall approval. "
                f"Canonical operation_id={item.get('operation_id') or 'n/a'}. "
                f"Declared agent status={status}. "
                "Permanent delete, raw DB, privilege changes, payment posting, and "
                "legal submission stay guarded or intentionally forbidden."
            ),
        )
    if not nodes:
        raise RuntimeError("generated Propreneur pack nodes catalog is empty")
    return nodes
