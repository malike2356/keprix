"""Shared types for product sidecar packs and invoke context."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeStatus(str, Enum):
    LIVE = "live"
    APPROVAL_REQUIRED = "approval_required"
    PROPOSAL_ONLY = "proposal_only"
    INTENTIONALLY_FORBIDDEN = "intentionally_forbidden"
    STUB = "stub"
    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"
    DEGRADED = "degraded"


class RiskClass(str, Enum):
    READ = "read"
    PROPOSE = "propose"
    MUTATE = "mutate"
    OUTBOUND = "outbound"
    DESTRUCTIVE = "destructive"
    HIGH_RISK = "high_risk"


class ErrorCode(str, Enum):
    DENIED = "denied"
    NOT_CONFIGURED = "not_configured"
    SOFT_WALL_REQUIRED = "soft_wall_required"
    BUDGET_EXCEEDED = "budget_exceeded"
    UNKNOWN_NODE = "unknown_node"
    PACK_DISABLED = "pack_disabled"
    CROSS_PRODUCT = "cross_product"
    VALIDATION = "validation"
    EXPIRED_TOKEN = "expired_token"
    WRONG_AUDIENCE = "wrong_audience"
    REPLAY = "replay"
    CIRCUIT_OPEN = "circuit_open"
    IDEMPOTENT_REPLAY = "idempotent_replay"


@dataclass(frozen=True)
class CapabilityNode:
    key: str
    version: str
    title: str
    product: str
    domain: str
    risk: RiskClass
    status: NodeStatus
    required_grants: tuple[str, ...] = ()
    entitlements: tuple[str, ...] = ()
    soft_wall: bool = False
    sync: bool = True
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    budget_units: int = 1
    idempotent: bool = False
    operator_guidance: str = ""
    aiva_sku_ok: bool = True
    carina_admin_only: bool = False


@dataclass
class RequestContext:
    product: str
    deployment: str
    workspace_id: str
    actor_id: str
    grants: frozenset[str]
    purpose: str
    correlation_id: str
    session_id: str = ""
    roles: tuple[str, ...] = ()
    entitlements: frozenset[str] = frozenset()
    shadow: bool = False
    engine_mode: str = "primary"  # primary | shadow | fallback
    audience: str = "keprix-product-sidecar"
    token_mode: str = "exchange"  # exchange | shared_compat


@dataclass
class ProductPackManifest:
    product_key: str
    pack_id: str
    version: str
    title: str
    contract_version: str
    nodes: dict[str, CapabilityNode]
    wrapper_of: str | None = None
    enabled: bool = True
    checksum: str = ""
    signature: str = ""
    connector: dict[str, Any] = field(default_factory=dict)
    policies: dict[str, Any] = field(default_factory=dict)
    memory_namespace: str = ""
    playbooks: tuple[str, ...] = ()
    events: tuple[str, ...] = ()
    migrations: tuple[str, ...] = ()
    feature_flag: str = ""
    last_known_good_version: str = ""

    def node_status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in self.nodes.values():
            counts[node.status.value] = counts.get(node.status.value, 0) + 1
        return counts

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "product_key": self.product_key,
            "pack_id": self.pack_id,
            "version": self.version,
            "title": self.title,
            "contract_version": self.contract_version,
            "checksum": self.checksum,
            "signature_present": bool(self.signature),
            "wrapper_of": self.wrapper_of,
            "enabled": self.enabled,
            "memory_namespace": self.memory_namespace,
            "playbooks": list(self.playbooks),
            "events": list(self.events),
            "migrations": list(self.migrations),
            "feature_flag": self.feature_flag,
            "node_counts": self.node_status_counts(),
            "nodes": sorted(self.nodes.keys()),
            "policies": dict(self.policies),
            "connector": {
                "default_deny": bool(self.connector.get("default_deny", True)),
                "no_sql": bool(self.connector.get("no_sql", True)),
                "routes": list(self.connector.get("routes") or []),
                "host_allowlist": list(self.connector.get("host_allowlist") or []),
                "base_url_env": self.connector.get("base_url_env"),
            },
        }
