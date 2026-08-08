"""KUS-00: architecture, public contract, compatibility and non-goals.

Architecture decision record (ADR) for the Universal Sidecar.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

CONTRACT_NAME = "keprix-universal-sidecar"
CONTRACT_VERSION = "1.0.0"
OPENAPI_VERSION = "3.1.0"
JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
CLOUDEVENTS_SPEC = "1.0"

# Separate from OpenAI-compatible /v1/chat/* and product packs /v1/products/*
SIDECAR_API_PREFIX = "/sidecar/v1"
DEFAULT_SIDECAR_HOST = "127.0.0.1"
DEFAULT_SIDECAR_PORT = 3360
MOUNTED_HOST = "127.0.0.1"
MOUNTED_PORT = 3333

BASELINE_VERSIONS: dict[str, str] = {
    "python": "3.11+",
    "node": "20+",
    "docker": "24+",
    "sqlite": "3.40+",
    "postgres": "15+",
    "openapi": OPENAPI_VERSION,
    "json_schema": "2020-12",
    "cloudevents": CLOUDEVENTS_SPEC,
    "http": "1.1+",
    "sse": "text/event-stream",
    "websocket": "optional-parity",
}

COMPATIBILITY_POLICY = (
    "Additive only within a major version. Breaking changes require a major bump "
    "and a documented migration window. Deprecations emit response headers "
    "(Deprecation, Sunset) and appear in doctor/conformance reports."
)

NON_GOALS: tuple[str, ...] = (
    "arbitrary database introspection or SQL passthrough",
    "UI scraping or browser automation via project manifest",
    "anonymous public agent endpoint",
    "unrestricted tool proxy or free-form HTTP from the model",
    "automatic write authority without declared apply + approval evidence",
    "secret values embedded in project manifests",
    "inline Python/JavaScript/shell/templates as capability definitions",
)

PRODUCT_PACK_MIGRATION: dict[str, dict[str, Any]] = {
    "carina": {
        "legacy_prefix": "/v1/products/carina",
        "universal_adapter": "product_key maps to project_key=carina with pack carina-aiva-sidecar",
        "status": "compatible",
    },
    "aiva": {
        "legacy_prefix": "/v1/products/aiva",
        "universal_adapter": "wrapper_of=carina; surface grants only",
        "status": "compatible",
    },
    "clinicom": {
        "legacy_prefix": "domain-packs/clinicom http_app :3353",
        "universal_adapter": "migrate pack under project_key=clinicom; keep southbound API",
        "status": "adapter_required",
    },
    "abbis": {
        "legacy_prefix": "pending product pack",
        "universal_adapter": "project_key=abbis once pack installed",
        "status": "planned",
    },
    "petraclus": {
        "legacy_prefix": "domain-packs/petraclus http_app :3362",
        "universal_adapter": "project_key=petraclus once pack installed",
        "status": "adapter_required",
    },
    "xeclone": {
        "legacy_prefix": "pending product pack",
        "universal_adapter": "project_key=xeclone once pack installed",
        "status": "planned",
    },
    "fleetz": {
        "legacy_prefix": "pending product pack",
        "universal_adapter": "project_key=fleetz once pack installed",
        "status": "planned",
    },
}


class DeploymentMode(str, Enum):
    PERSONAL_OS = "personal_os"
    MOUNTED = "mounted"
    SIDECAR_ONLY = "sidecar_only"
    DEDICATED_PER_PROJECT = "dedicated_per_project"
    SHARED_HARD_ISOLATED = "shared_hard_isolated"


MODE_SAFETY: dict[DeploymentMode, dict[str, Any]] = {
    DeploymentMode.PERSONAL_OS: {
        "safe_when": "single operator, local loopback, no multi-tenant product traffic",
        "supported": True,
    },
    DeploymentMode.MOUNTED: {
        "safe_when": "sidecar routes on existing Keprix backend (:3333), private network",
        "supported": True,
    },
    DeploymentMode.SIDECAR_ONLY: {
        "safe_when": "reduced process on :3360 without admin/workspace UI",
        "supported": True,
    },
    DeploymentMode.DEDICATED_PER_PROJECT: {
        "safe_when": "one Keprix process per product deployment (preferred production)",
        "supported": True,
    },
    DeploymentMode.SHARED_HARD_ISOLATED: {
        "safe_when": "isolation tests prove no cross-project enumeration; otherwise forbidden",
        "supported": True,
        "requires": "isolation_matrix_pass",
    },
}


OWNERSHIP = {
    "project_owns": (
        "users",
        "tenancy",
        "entitlements",
        "business_records",
        "UI",
        "side_effects",
    ),
    "keprix_owns": (
        "agent_execution",
        "configured_capabilities",
        "memory",
        "jobs",
        "policy",
        "approvals",
        "audit",
    ),
}


IDENTIFIER_KINDS: tuple[str, ...] = (
    "project",
    "deployment",
    "environment",
    "tenant",
    "actor",
    "session",
    "subject",
    "capability",
    "run",
    "job",
    "approval",
    "event",
    "artifact",
)


THREAT_MODELS: dict[str, dict[str, Any]] = {
    "local_same_host": {
        "trust": "loopback + pairing code",
        "risks": ("local malware", "misbound 0.0.0.0"),
        "mitigations": ("default 127.0.0.1", "refuse public bind without TLS/auth"),
    },
    "docker_network": {
        "trust": "private compose network",
        "risks": ("container escape", "SSRF to metadata"),
        "mitigations": ("NetworkPolicy", "connector IP allowlists", "no host docker.sock"),
    },
    "remote_private_network": {
        "trust": "mTLS or short-lived tokens + private DNS",
        "risks": ("token theft", "confused deputy"),
        "mitigations": ("audience binding", "grant ceilings", "audit"),
    },
    "reverse_connect": {
        "trust": "project initiates outbound mTLS/poll",
        "risks": ("stale work after cancel", "broader grant smuggling"),
        "mitigations": ("same grant ceiling as direct", "idempotency", "cursor"),
    },
    "air_gap": {
        "trust": "offline bundle, no telemetry",
        "risks": ("stale signed packs", "unsigned extensions"),
        "mitigations": ("signed wheels/images", "no hidden update calls"),
    },
}


DEGRADATION = {
    "keprix_outage": (
        "project continues independently",
        "callbacks queue with bounded TTL",
        "no blocking of product shutdown on sidecar drain",
        "readiness false while draining",
    ),
    "config_trust": (
        "manifest requests capabilities",
        "installed runtime policy is upper bound",
        "unknown/denied nodes fail validation honestly",
    ),
}


def architecture_summary() -> dict[str, Any]:
    return {
        "contract": {"name": CONTRACT_NAME, "version": CONTRACT_VERSION},
        "api_prefix": SIDECAR_API_PREFIX,
        "ports": {
            "mounted": {"host": MOUNTED_HOST, "port": MOUNTED_PORT},
            "sidecar_only": {"host": DEFAULT_SIDECAR_HOST, "port": DEFAULT_SIDECAR_PORT},
        },
        "compatibility_policy": COMPATIBILITY_POLICY,
        "ownership": OWNERSHIP,
        "identifiers": list(IDENTIFIER_KINDS),
        "deployment_modes": {
            mode.value: MODE_SAFETY[mode] for mode in DeploymentMode
        },
        "threat_models": THREAT_MODELS,
        "degradation": DEGRADATION,
        "baseline_versions": BASELINE_VERSIONS,
        "product_pack_migration": PRODUCT_PACK_MIGRATION,
        "non_goals": list(NON_GOALS),
        "openai_chat_compat": "unchanged; /v1/chat/* remains separate",
        "product_sidecar_compat": "/v1/products/{key} remains; universal uses /sidecar/v1/projects/{key}",
    }
