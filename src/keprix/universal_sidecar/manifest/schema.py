"""JSON Schema and Python helpers for keprix.sidecar.yaml (KUS-01)."""

from __future__ import annotations

from typing import Any

CONTRACT_VERSION = "1.0.0"

# Forbidden substrings / patterns that indicate embedded secrets or hooks.
SECRET_FIELD_HINTS = (
    "password",
    "api_key",
    "apikey",
    "secret",
    "private_key",
    "token_value",
    "access_key",
)

EXECUTABLE_HOOK_KEYS = (
    "hooks",
    "pre_invoke",
    "post_invoke",
    "import",
    "exec",
    "eval",
    "python",
    "javascript",
    "shell",
    "inline_code",
    "dynamic_import",
)

BLOCKED_URI_SCHEMES = frozenset(
    {"file", "ftp", "gopher", "data", "javascript", "dict", "ldap"}
)

BLOCKED_HOST_SUFFIXES = (
    "metadata.google.internal",
    "metadata.azure.com",
    "169.254.169.254",
)


def manifest_json_schema() -> dict[str, Any]:
    """Return the canonical JSON Schema for keprix.sidecar.yaml."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://keprix.dev/schemas/universal-sidecar/keprix.sidecar.schema.json",
        "title": "Keprix Universal Sidecar Project Manifest",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "contract_version",
            "project_key",
            "display_name",
            "deployment",
            "environment",
            "base_url",
            "auth",
        ],
        "properties": {
            "contract_version": {"type": "string", "const": CONTRACT_VERSION},
            "project_key": {
                "type": "string",
                "pattern": "^[a-z][a-z0-9_-]{1,63}$",
            },
            "display_name": {"type": "string", "minLength": 1, "maxLength": 128},
            "deployment": {"type": "string", "minLength": 1, "maxLength": 64},
            "environment": {
                "type": "string",
                "enum": ["local", "dev", "staging", "prod", "airgap"],
            },
            "base_url": {"type": "string", "format": "uri", "maxLength": 512},
            "callback_urls": {
                "type": "array",
                "items": {"type": "string", "format": "uri"},
                "maxItems": 16,
                "default": [],
            },
            "auth": {
                "type": "object",
                "additionalProperties": False,
                "required": ["profile"],
                "properties": {
                    "profile": {
                        "type": "string",
                        "enum": [
                            "bearer",
                            "oauth_client_credentials",
                            "mtls",
                            "hmac",
                            "static_header",
                        ],
                    },
                    "vault_ref": {"type": "string", "pattern": "^(vault|env|secret):.+"},
                    "header_name": {"type": "string"},
                    "audience": {"type": "string"},
                },
            },
            "tenant_actor_mapping": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "tenant_claim": {"type": "string"},
                    "actor_claim": {"type": "string"},
                    "require_signed_assertion": {"type": "boolean", "default": True},
                },
            },
            "requested_packs": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
            },
            "capabilities": {
                "type": "array",
                "items": {"$ref": "#/$defs/capability_binding"},
                "default": [],
            },
            "connectors": {
                "type": "array",
                "items": {"$ref": "#/$defs/connector_operation"},
                "default": [],
            },
            "events": {
                "type": "array",
                "items": {"$ref": "#/$defs/event_decl"},
                "default": [],
            },
            "webhooks": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "signature": {
                        "type": "string",
                        "enum": ["hmac-sha256", "ed25519"],
                        "default": "hmac-sha256",
                    },
                    "max_attempts": {"type": "integer", "minimum": 1, "maximum": 20},
                    "vault_ref": {"type": "string", "pattern": "^(vault|env|secret):.+"},
                },
            },
            "context_slices": {
                "type": "array",
                "items": {"$ref": "#/$defs/context_slice"},
                "default": [],
            },
            "memory": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": [
                            "disabled",
                            "ephemeral",
                            "project_facts",
                            "subject",
                            "shared_approved",
                        ],
                        "default": "ephemeral",
                    },
                    "retention_days": {"type": "integer", "minimum": 0, "maximum": 3650},
                    "namespaces": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                },
            },
            "approvals": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "required_for_risk": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["propose", "mutate", "outbound", "destructive", "high_risk"],
                        },
                        "default": ["mutate", "outbound", "destructive", "high_risk"],
                    },
                    "ttl_seconds": {"type": "integer", "minimum": 60, "maximum": 86400},
                },
            },
            "budgets": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "requests_per_minute": {"type": "integer", "minimum": 1},
                    "jobs_concurrent": {"type": "integer", "minimum": 1},
                    "tokens_per_day": {"type": "integer", "minimum": 0},
                    "cost_gbp_per_day": {"type": "number", "minimum": 0},
                    "callback_per_hour": {"type": "integer", "minimum": 1},
                    "storage_mb": {"type": "integer", "minimum": 1},
                },
            },
            "retention": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "events_days": {"type": "integer", "minimum": 0},
                    "jobs_days": {"type": "integer", "minimum": 0},
                    "artifacts_days": {"type": "integer", "minimum": 0},
                    "audit_days": {"type": "integer", "minimum": 1},
                },
            },
            "egress": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "allow_private_networks": {"type": "boolean", "default": False},
                    "allow_loopback": {"type": "boolean", "default": False},
                    "allowed_hosts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                },
            },
            "feature_flags": {
                "type": "object",
                "additionalProperties": {"type": "boolean"},
                "default": {},
            },
        },
        "$defs": {
            "connector_operation": {
                "type": "object",
                "additionalProperties": False,
                "required": ["key", "method", "path", "purpose"],
                "properties": {
                    "key": {"type": "string", "pattern": "^[a-z][a-z0-9_.-]{1,63}$"},
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
                    "path": {"type": "string", "pattern": "^/", "maxLength": 256},
                    "purpose": {"type": "string"},
                    "request_schema_ref": {"type": "string"},
                    "response_schema_ref": {"type": "string"},
                    "pagination": {"type": ["object", "null"]},
                    "projection": {"type": ["array", "null"], "items": {"type": "string"}},
                    "grants": {"type": "array", "items": {"type": "string"}, "default": []},
                    "sensitivity": {
                        "type": "string",
                        "enum": ["public", "internal", "pii_minimised", "sensitive"],
                        "default": "internal",
                    },
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 120, "default": 15},
                    "rate_per_minute": {"type": "integer", "minimum": 1, "default": 60},
                    "cache_ttl_seconds": {"type": "integer", "minimum": 0, "default": 0},
                    "retry": {"type": "object"},
                    "idempotency": {"type": "boolean", "default": False},
                    "approval_required": {"type": "boolean", "default": False},
                    "mode": {
                        "type": "string",
                        "enum": ["read", "preview", "propose", "apply"],
                        "default": "read",
                    },
                },
            },
            "capability_binding": {
                "type": "object",
                "additionalProperties": False,
                "required": ["node", "version"],
                "properties": {
                    "node": {"type": "string"},
                    "version": {"type": "string"},
                    "alias": {"type": "string"},
                    "scopes": {"type": "array", "items": {"type": "string"}, "default": []},
                    "input_defaults": {"type": "object"},
                    "context_sources": {"type": "array", "items": {"type": "string"}, "default": []},
                    "model_constraints": {"type": "object"},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 600},
                    "budget_units": {"type": "integer", "minimum": 1},
                    "ui_description": {"type": "string"},
                },
            },
            "event_decl": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type", "direction"],
                "properties": {
                    "type": {"type": "string"},
                    "schema": {"type": "string"},
                    "direction": {"type": "string", "enum": ["inbound", "outbound", "both"]},
                    "sensitivity": {"type": "string"},
                    "dedupe": {"type": "boolean", "default": True},
                    "delivery": {"type": "string", "enum": ["at_least_once", "exactly_once_best_effort"]},
                    "callback": {"type": "string"},
                    "retention_days": {"type": "integer", "minimum": 0},
                },
            },
            "context_slice": {
                "type": "object",
                "additionalProperties": False,
                "required": ["key", "purpose"],
                "properties": {
                    "key": {"type": "string"},
                    "purpose": {"type": "string"},
                    "schema": {"type": "string"},
                    "operation": {"type": "string"},
                    "event": {"type": "string"},
                    "sensitivity": {"type": "string"},
                    "ttl_seconds": {"type": "integer", "minimum": 1},
                    "max_records": {"type": "integer", "minimum": 1},
                    "max_bytes": {"type": "integer", "minimum": 1},
                    "required_grants": {"type": "array", "items": {"type": "string"}},
                    "allowed_nodes": {"type": "array", "items": {"type": "string"}},
                    "redaction": {"type": "object"},
                },
            },
        },
    }


# Built-in safe nodes available to universal quickstart (KUS-05).
SAFE_BUILTIN_NODES: frozenset[str] = frozenset(
    {
        "prompt.transform",
        "classify",
        "summarise",
        "extract",
        "compare",
        "validate",
        "memory.retrieve",
        "project.read",
        "proposal.prepare",
        "wait",
        "decision",
        "approval.request",
        "event.emit",
        "finish",
    }
)

# Disabled in universal quickstart; require installed capability + sandbox.
DANGEROUS_NODE_PREFIXES: tuple[str, ...] = (
    "shell.",
    "fs.",
    "browser.",
    "network.",
    "code.",
    "mutate.",
    "send.",
    "exec.",
)

SCOPE_CATALOG: frozenset[str] = frozenset(
    {
        "discover",
        "jobs",
        "events",
        "approvals",
        "metrics",
        "files",
        "administration",
        # patterns: invoke:{node}, connector:{op}, memory:{ns/action}
    }
)

HIGH_RISK_SCOPES: frozenset[str] = frozenset(
    {
        "administration",
        "files",
        "connector:apply",
        "invoke:shell",
        "invoke:network",
        "invoke:code",
    }
)
