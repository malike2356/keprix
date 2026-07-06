"""Final output and artifact validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from keprix.typed_agents.schemas import ArtifactMetadata, HandoffPayload, ValidationRepairMessage
from keprix.typed_agents.tool_validation import pydantic_errors


def validate_output(output_type: type[BaseModel], raw: Any) -> tuple[BaseModel | None, ValidationRepairMessage | None]:
    try:
        if isinstance(raw, output_type):
            return raw, None
        if isinstance(raw, BaseModel):
            return output_type.model_validate(raw.model_dump()), None
        if isinstance(raw, dict):
            return output_type.model_validate(raw), None
        return output_type.model_validate_json(str(raw)), None
    except ValidationError as exc:
        return None, ValidationRepairMessage(
            kind="final_output",
            message="Final agent output failed validation. Repair the response and retry.",
            errors=pydantic_errors(exc),
        )


def validate_artifact_metadata(raw: dict[str, Any]) -> tuple[ArtifactMetadata | None, ValidationRepairMessage | None]:
    try:
        return ArtifactMetadata.model_validate(raw), None
    except ValidationError as exc:
        return None, ValidationRepairMessage(
            kind="artifact_metadata",
            message="Artifact metadata failed validation.",
            errors=pydantic_errors(exc),
        )


def validate_handoff_payload(raw: dict[str, Any]) -> tuple[HandoffPayload | None, ValidationRepairMessage | None]:
    try:
        return HandoffPayload.model_validate(raw), None
    except ValidationError as exc:
        return None, ValidationRepairMessage(
            kind="handoff_payload",
            message="Handoff payload failed validation.",
            errors=pydantic_errors(exc),
        )
