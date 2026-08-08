"""Honest capability nodes and model routing for Clinicom pack."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

PACK_VERSION = "0.2.0"
CONTRACT_VERSION = "2.0"
PRODUCT_KEY = "clinicom"

# Bare HTTP path names used by local clone / Carina, plus prefixed aliases used by Clinicom provider.
CORE_TOOLS = ("transcribe", "translate", "simplify", "speak", "product_help")
DEEP_TOOLS = (
    "cultural_adapt",
    "teachback_score",
    "safety_triage_assist",
    "session_digest",
    "specialty_simplify",
    "confidence_explain",
)

TOOL_ALIASES: dict[str, str] = {
    "transcribe": "clinicom_transcribe",
    "translate": "clinicom_translate",
    "simplify": "clinicom_simplify",
    "speak": "clinicom_speak",
    "product_help": "clinicom_product_help",
    "cultural_adapt": "clinicom_cultural_adapt",
    "teachback_score": "clinicom_teachback_score",
    "safety_triage_assist": "clinicom_safety_triage_assist",
    "session_digest": "clinicom_session_digest",
    "specialty_simplify": "clinicom_specialty_simplify",
    "confidence_explain": "clinicom_confidence_explain",
    # Prefixed aliases map to same handlers
    "clinicom_cultural_adapt": "clinicom_cultural_adapt",
    "clinicom_teachback_score": "clinicom_teachback_score",
    "clinicom_safety_triage_assist": "clinicom_safety_triage_assist",
    "clinicom_session_digest": "clinicom_session_digest",
    "clinicom_specialty_simplify": "clinicom_specialty_simplify",
    "clinicom_confidence_explain": "clinicom_confidence_explain",
    "clinicom_transcribe": "clinicom_transcribe",
    "clinicom_translate": "clinicom_translate",
    "clinicom_simplify": "clinicom_simplify",
    "clinicom_speak": "clinicom_speak",
    "clinicom_product_help": "clinicom_product_help",
}

LATENCY = {
    "transcribe": "high",
    "translate": "high",
    "simplify": "high",
    "speak": "high",
    "product_help": "low",
    "cultural_adapt": "medium",
    "teachback_score": "medium",
    "safety_triage_assist": "medium",
    "session_digest": "low",
    "specialty_simplify": "medium",
    "confidence_explain": "low",
}

SAFETY_CLASS = {
    "transcribe": "communication_assist",
    "translate": "communication_assist",
    "simplify": "communication_assist",
    "speak": "communication_assist",
    "product_help": "product_help",
    "cultural_adapt": "communication_assist",
    "teachback_score": "quality_assist",
    "safety_triage_assist": "safety_assist_signal",
    "session_digest": "communication_assist",
    "specialty_simplify": "communication_assist",
    "confidence_explain": "quality_assist",
}

ENTITLEMENT = {
    "transcribe": "core",
    "translate": "core",
    "simplify": "core",
    "speak": "core",
    "product_help": "core",
    "cultural_adapt": "deep_ai_tools",
    "teachback_score": "deep_ai_tools",
    "safety_triage_assist": "deep_ai_tools",
    "session_digest": "deep_ai_tools",
    "specialty_simplify": "deep_ai_tools",
    "confidence_explain": "deep_ai_tools",
}


def _gemini_configured() -> bool:
    return bool(
        (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("KEPRIX_GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("CLINICOM_GEMINI_API_KEY")
            or ""
        ).strip()
    )


def _ml_reachable(timeout: float = 1.5) -> bool:
    base = os.environ.get("KEPRIX_ML_SERVICE_URL", "").rstrip("/")
    if not base:
        return False
    try:
        req = urllib.request.Request(f"{base}/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 500
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        # Some ML services lack /health; treat configured URL as available for routing honesty.
        return True


def provider_health() -> dict[str, Any]:
    ml = bool(os.environ.get("KEPRIX_ML_SERVICE_URL", "").strip())
    ml_ok = _ml_reachable() if ml else False
    gemini = _gemini_configured()
    if ml_ok:
        primary = "keprix-ml-service"
        status = "live"
    elif gemini:
        primary = "keprix-gemini"
        status = "live"
    else:
        primary = "keprix-clinicom-stub"
        status = "stub"
    return {
        "ml_configured": ml,
        "ml_reachable": ml_ok,
        "gemini_configured": gemini,
        "primary": primary,
        "status": status,
        "fallback_order": [
            "keprix-ml-service",
            "keprix-gemini",
            "keprix-clinicom-stub",
        ],
        "hidden_fallback": False,
    }


def canonical_tool_name(name: str) -> str:
    key = str(name or "").strip()
    if key in TOOL_ALIASES:
        return TOOL_ALIASES[key]
    if key.startswith("clinicom_"):
        return key
    return TOOL_ALIASES.get(key, key)


def bare_tool_name(registry_name: str) -> str:
    name = str(registry_name or "")
    if name.startswith("clinicom_"):
        bare = name[len("clinicom_") :]
        if bare in CORE_TOOLS or bare in DEEP_TOOLS:
            return bare
    return name


def tool_status_for(bare: str, health: dict[str, Any] | None = None) -> dict[str, Any]:
    health = health or provider_health()
    is_core = bare in CORE_TOOLS
    is_deep = bare in DEEP_TOOLS
    if not (is_core or is_deep):
        return {"status": "disabled", "source": "unknown", "latency_class": "low"}

    if health["status"] == "live":
        status = "live"
        source = health["primary"]
    else:
        status = "stub"
        source = "keprix-clinicom-stub"

    # product_help and confidence_explain can be honest stubs without claiming AI
    if bare in {"product_help", "confidence_explain", "session_digest", "teachback_score"} and health["status"] != "live":
        status = "stub"
        source = "keprix-clinicom-stub"

    return {
        "status": status,
        "source": source,
        "latency_class": LATENCY.get(bare, "medium"),
        "requires_auth": bool(os.environ.get("CLINICOM_SHARED_TOKEN") or os.environ.get("CLINICOM_SIDECAR_TOKEN")),
        "safety_class": SAFETY_CLASS.get(bare, "communication_assist"),
        "entitlement": ENTITLEMENT.get(bare, "core"),
        "fallback": "keprix-clinicom-stub",
        "modality": "audio" if bare in {"transcribe", "speak"} else "text",
    }


def capability_tools(health: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    health = health or provider_health()
    tools: list[dict[str, Any]] = []
    for bare in (*CORE_TOOLS, *DEEP_TOOLS):
        meta = tool_status_for(bare, health)
        aliases = [bare, f"clinicom_{bare}"] if bare in DEEP_TOOLS else [bare]
        if bare in DEEP_TOOLS:
            # Advertise both bare and prefixed names for contract 2.0 consumers
            for name in aliases:
                tools.append(
                    {
                        "name": name,
                        "canonical": f"clinicom_{bare}",
                        "aliases": aliases,
                        **meta,
                    }
                )
        else:
            tools.append(
                {
                    "name": bare,
                    "canonical": f"clinicom_{bare}",
                    "aliases": [bare, f"clinicom_{bare}"],
                    **meta,
                }
            )
    return tools


def capability_nodes(health: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    health = health or provider_health()
    nodes: list[dict[str, Any]] = []
    for bare in (*CORE_TOOLS, *DEEP_TOOLS):
        meta = tool_status_for(bare, health)
        nodes.append(
            {
                "key": f"clinicom.{bare}",
                "version": PACK_VERSION,
                "title": bare.replace("_", " ").title(),
                "product": PRODUCT_KEY,
                "domain": "healthcare_communication",
                "execution": "sync",
                "classification": (
                    "read"
                    if bare in {"confidence_explain", "product_help", "session_digest", "teachback_score"}
                    else "propose"
                ),
                "high_risk": bare == "safety_triage_assist",
                "required_grants": [ENTITLEMENT.get(bare, "core")],
                "entitlements": [ENTITLEMENT.get(bare, "core")],
                "approvals": ["clinician_acceptance"] if bare != "product_help" else [],
                "accepted_context_slices": [
                    "runtime_provider_policy",
                    "organisation_language_specialty",
                    "consent",
                    "session_safe_glossary",
                    "turn_by_id",
                    "entitlement",
                ],
                "emitted_events": [
                    "transform.requested",
                    "transform.completed",
                ],
                "cost_class": meta["latency_class"],
                "timeout_seconds": 45 if meta["latency_class"] == "high" else 20,
                "concurrency_limit": 8,
                "retry_policy": "bounded_idempotent_only",
                "idempotency": "client_key_required_for_mutate",
                "cancellation": True,
                "data_classes": ["communication_text", "optional_audio"],
                "retention": "transient_unless_product_persists",
                "redaction": "no_raw_patient_identifiers_by_default",
                "residency": "GB",
                "model_requirements": health["fallback_order"],
                "deterministic_fallback": "keprix-clinicom-stub",
                "health_dependencies": ["ml_or_gemini_or_stub"],
                "status": meta["status"],
                "source": meta["source"],
                "operator_guidance": (
                    "Stub/fallback must be labelled; never present as live AI."
                    if meta["status"] != "live"
                    else "Live AI path; preserve numbers/negation; clinician acceptance required for durable write."
                ),
                "safety_class": meta["safety_class"],
                "aliases": [bare, f"clinicom_{bare}"],
                "schemas_ref": f"schemas.json#{bare}",
            }
        )
    return nodes


def capabilities_payload() -> dict[str, Any]:
    health = provider_health()
    tools = capability_tools(health)
    sources = {t["name"]: t["source"] for t in tools if t["name"] in CORE_TOOLS or t["name"].startswith("clinicom_")}
    return {
        "contract_version": CONTRACT_VERSION,
        "profile": "keprix",
        "pack_version": PACK_VERSION,
        "tools": tools,
        "nodes": capability_nodes(health),
        "provider_sources": sources,
        "provider_health": health,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "never_diagnose_or_prescribe": True,
        "responsibility": {
            "product_owns": [
                "patient_truth",
                "session_truth",
                "consent",
                "auth",
                "entitlements",
                "ehr",
                "ui",
                "clinical_workflow",
            ],
            "keprix_owns": [
                "scoped_communication_transforms",
                "assistive_safety_signals",
                "handoff_drafts",
            ],
        },
    }


def pack_manifest() -> dict[str, Any]:
    return {
        "product_key": PRODUCT_KEY,
        "pack_id": PRODUCT_KEY,
        "version": PACK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "compatibility": {"clinicom_min": "2.0"},
        "policy": {
            "no_ehr_write": True,
            "no_autonomous_clinical_decision": True,
            "data_minimisation": True,
            "contabo_default_profile": "carina",
        },
        "migrations": [],
        "checksum_note": "Verify pack tree before Contabo start; provision emits receipt without secrets.",
        "northbound": [
            "/health",
            "/clinicom/capabilities",
            "/clinicom/tools/{name}",
            "/v1/products/clinicom/*",
        ],
    }
