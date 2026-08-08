"""OpenAPI fragment and runtime capability schema agreement helpers."""

from __future__ import annotations

from typing import Any

from keprix.product_sidecar.registry import get_product_pack_registry
from keprix.product_sidecar.types import ErrorCode, NodeStatus, RiskClass

NORTHBOUND_PATHS = (
    "/health",
    "/capabilities",
    "/manifest",
    "/sessions",
    "/invoke",
    "/jobs",
    "/jobs/{job_id}",
    "/jobs/{job_id}/cancel",
    "/events",
    "/events/stream",
    "/approvals/{approval_id}/decision",
    "/metrics",
)


STABLE_PRODUCTS = (
    "petraclus",
    "abbis",
    "xeclone",
    "fleetz",
    "clinicom",
    "carina",
    "aiva",
    "propreneur",
)


def openapi_fragment() -> dict[str, Any]:
    """Stable OpenAPI-shaped contract description for product sidecar."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Keprix product sidecar",
            "version": "1.0.0",
            "description": "Northbound /v1/products/{product_key} contract",
        },
        "paths": {
            f"/v1/products/{{product_key}}{path}": {"summary": path.strip("/")}
            for path in NORTHBOUND_PATHS
        },
        "components": {
            "schemas": {
                "CapabilityNode": {
                    "type": "object",
                    "required": ["key", "status", "risk", "required_grants"],
                    "properties": {
                        "key": {"type": "string"},
                        "status": {"enum": [s.value for s in NodeStatus]},
                        "risk": {"enum": [r.value for r in RiskClass]},
                        "required_grants": {"type": "array", "items": {"type": "string"}},
                        "soft_wall": {"type": "boolean"},
                        "sync": {"type": "boolean"},
                    },
                },
                "Error": {
                    "type": "object",
                    "required": ["code"],
                    "properties": {
                        "code": {"enum": [e.value for e in ErrorCode]},
                        "error": {"type": "string"},
                    },
                },
            }
        },
        "x-keprix-contract-version": "1.0.0",
        "x-stable-error-codes": [e.value for e in ErrorCode],
        "x-products": list(STABLE_PRODUCTS),
        "x-propreneur-compat": {
            "agent_run": "/carina/agent/run",
            "tools_catalog": "/api/carina/tools",
            "tools_execute": "/api/carina/tools/{toolName}",
        },
    }


def runtime_agrees_with_openapi(product_key: str = "carina") -> dict[str, Any]:
    pack = get_product_pack_registry().require(product_key)
    openapi = openapi_fragment()
    status_enum = set(openapi["components"]["schemas"]["CapabilityNode"]["properties"]["status"]["enum"])
    risk_enum = set(openapi["components"]["schemas"]["CapabilityNode"]["properties"]["risk"]["enum"])
    mismatches: list[str] = []
    for node in pack.nodes.values():
        if node.status.value not in status_enum:
            mismatches.append(f"status:{node.key}:{node.status.value}")
        if node.risk.value not in risk_enum:
            mismatches.append(f"risk:{node.key}:{node.risk.value}")
    return {
        "ok": not mismatches,
        "mismatches": mismatches,
        "contract_version": pack.contract_version,
        "openapi_version": openapi["info"]["version"],
        "paths": list(openapi["paths"].keys()),
    }
