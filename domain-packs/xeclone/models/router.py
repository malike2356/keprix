"""Deterministic model router for Wave 1 stubs."""

from __future__ import annotations

from typing import Any

ROUTES: dict[str, dict[str, Any]] = {
    "text": {
        "provider": "local-deterministic",
        "modality": "text",
        "data_use": "inference_only",
        "retention": "none",
        "residency": "local",
        "fallback": "local-deterministic",
        "consent_eligibility": ["generate", "transform"],
        "cost": "fixture",
    },
    "audio": {
        "provider": "stub-tts",
        "modality": "audio",
        "data_use": "inference_only_no_train",
        "retention": "artifact_expiry",
        "residency": "local_stub",
        "fallback": "text_only_draft",
        "consent_eligibility": ["generate", "upload_to_provider"],
        "cost": "fixture",
    },
    "image": {
        "provider": "stub-image",
        "modality": "image",
        "data_use": "inference_only_no_train",
        "retention": "artifact_expiry",
        "residency": "local_stub",
        "fallback": "text_only_draft",
        "consent_eligibility": ["generate", "upload_to_provider"],
        "cost": "fixture",
    },
    "video": {
        "provider": "stub-video",
        "modality": "video",
        "data_use": "inference_only_no_train",
        "retention": "artifact_expiry",
        "residency": "local_stub",
        "fallback": "text_only_draft",
        "consent_eligibility": ["generate", "upload_to_provider"],
        "cost": "fixture",
    },
}


def route_for(domain: str) -> dict[str, Any]:
    return dict(ROUTES.get(domain) or ROUTES["text"])


def reject_if_incompatible(*, domain: str, purposes: list[str]) -> dict[str, Any]:
    route = route_for(domain)
    allowed = set(route.get("consent_eligibility") or [])
    missing = [p for p in purposes if p not in allowed and p in {"generate", "upload_to_provider", "train"}]
    # train is never allowed on provider routes in Wave 1
    if "train" in purposes:
        return {"ok": False, "reason": "provider_training_disabled"}
    if missing and domain != "text":
        return {"ok": False, "reason": "consent_incompatible_transfer", "missing": missing}
    return {"ok": True, "route": route}
