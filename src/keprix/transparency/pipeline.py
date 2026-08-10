"""Middleware helpers wrapping every AI model call: consent → log → label."""

from __future__ import annotations

from typing import Any

from keprix.transparency.config import generation_log_enabled, labeling_enabled
from keprix.transparency.consent_gate import ConsentRequiredError, get_consent_gate
from keprix.transparency.generation_log import get_generation_log_store
from keprix.transparency.labels import ContentType, SgiLabeler


def prepare_ai_call(user_id: str | None, feature: str = "text_generation") -> dict[str, Any]:
    """Block before any user input enters an AI model when consent is missing."""
    return get_consent_gate().require_consent(user_id or "local", feature)


def finalize_ai_output(
    *,
    input_payload: Any,
    output_payload: Any,
    model_name: str,
    user_id: str | None,
    content_type: ContentType = "text",
    feature_endpoint: str = "chat",
    session_id: str | None = None,
    workspace_id: str = "default",
    model_version: str | None = None,
    locale: str = "en",
    feature: str = "text_generation",
    label: bool = True,
) -> dict[str, Any]:
    """Log generation (hashes) and attach SGI disclosure to the output."""
    prepare_ai_call(user_id, feature)

    log_row = None
    if generation_log_enabled():
        log_row = get_generation_log_store().log_generation(
            input_payload=input_payload,
            output_payload=output_payload,
            model_name=model_name,
            user_id=user_id or "local",
            content_type=content_type,
            feature_endpoint=feature_endpoint,
            session_id=session_id,
            workspace_id=workspace_id,
            model_version=model_version,
            locale=locale,
        )

    labeled: dict[str, Any] = {
        "labeled_output": output_payload,
        "disclosure": None,
        "label": None,
        "metadata": {},
    }
    if label and labeling_enabled():
        labeled = SgiLabeler().label_output(
            output_payload,
            content_type,
            locale=locale,
            model_name=model_name,
        )

    return {
        "log": log_row,
        "labeled_output": labeled.get("labeled_output"),
        "disclosure": labeled.get("disclosure"),
        "label": labeled.get("label"),
        "metadata": labeled.get("metadata") or {},
    }


__all__ = ["ConsentRequiredError", "finalize_ai_output", "prepare_ai_call"]
