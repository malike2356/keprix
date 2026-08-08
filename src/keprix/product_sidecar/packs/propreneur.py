"""Propreneur product pack node catalog for the shared product_sidecar registry."""

from __future__ import annotations

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
    "stub": NodeStatus.STUB,
    "not_configured": NodeStatus.NOT_CONFIGURED,
    "disabled": NodeStatus.DISABLED,
    "degraded": NodeStatus.DEGRADED,
}

# UK property MIS capability surface. Reads and mutates call Propreneur HTTP tools.
# soft_wall=True for mutate / destructive / propose. No outbound unless messaging.
_SPECS: list[tuple[str, str, str, str, str, bool]] = [
    # key, title, domain, risk, status, soft_wall
    ("property_search", "Property search", "property", "read", "live", False),
    ("property_get", "Property get", "property", "read", "live", False),
    ("property_create", "Property create", "property", "mutate", "live", True),
    ("property_update", "Property update", "property", "mutate", "live", True),
    ("property_archive", "Property archive", "property", "destructive", "live", True),
    ("contact_search", "Contact search", "contact", "read", "live", False),
    ("contact_get", "Contact get", "contact", "read", "live", False),
    ("contact_create", "Contact create", "contact", "mutate", "live", True),
    ("contact_update", "Contact update", "contact", "mutate", "live", True),
    ("tenancy_search", "Tenancy search", "tenancy", "read", "live", False),
    ("tenancy_get", "Tenancy get", "tenancy", "read", "live", False),
    ("tenancy_create", "Tenancy create", "tenancy", "mutate", "live", True),
    ("tenancy_update", "Tenancy update", "tenancy", "mutate", "live", True),
    ("deal_search", "Deal search", "deal", "read", "live", False),
    ("deal_get", "Deal get", "deal", "read", "live", False),
    ("deal_propose", "Deal propose", "deal", "propose", "live", True),
    ("compliance_get", "Compliance get", "compliance", "read", "live", False),
    ("compliance_propose", "Compliance propose", "compliance", "high_risk", "live", True),
    ("maintenance_search", "Maintenance search", "maintenance", "read", "live", False),
    ("maintenance_propose", "Maintenance propose", "maintenance", "propose", "live", True),
    ("expense_propose", "Expense propose", "finance", "high_risk", "live", True),
    ("financial_log_propose", "Financial log propose", "finance", "high_risk", "live", True),
    ("team_invite_propose", "Team invite propose", "access", "high_risk", "live", True),
    ("task_create", "Task create", "ops", "mutate", "live", True),
    ("note_create", "Note create", "ops", "mutate", "live", True),
    ("ask_portfolio", "Ask portfolio", "portfolio", "read", "live", False),
    ("sync_health", "Sync health", "sync", "read", "live", False),
]


def build_propreneur_nodes() -> dict[str, CapabilityNode]:
    nodes: dict[str, CapabilityNode] = {}
    for key, title, domain, risk, status, soft_wall in _SPECS:
        nodes[key] = CapabilityNode(
            key=key,
            version="1.0.0",
            title=title,
            product="propreneur",
            domain=domain,
            risk=_RISK[risk],
            status=_STATUS[status],
            required_grants=(f"node:{key}",),
            entitlements=("propreneur",),
            soft_wall=soft_wall,
            sync=True,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            idempotent=key.endswith("_get") or key.endswith("_search") or key == "ask_portfolio",
            operator_guidance=(
                "UK property MIS pack; Propreneur remains authorization and data authority. "
                "Mutate, destructive, and propose nodes require soft-wall approval."
            ),
        )
    return nodes
