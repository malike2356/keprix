"""Tool argument and return validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from keprix.typed_agents.schemas import ValidationRepairMessage


def pydantic_errors(exc: ValidationError) -> list[dict[str, Any]]:
    return [
        {
            "loc": list(error.get("loc", ())),
            "msg": error.get("msg", "invalid"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]


def validate_tool_arguments(tool_name: str, input_model: type[BaseModel], raw: dict[str, Any]) -> tuple[BaseModel | None, ValidationRepairMessage | None]:
    try:
        return input_model.model_validate(raw), None
    except ValidationError as exc:
        return None, ValidationRepairMessage(
            kind="tool_arguments",
            message=f"Tool '{tool_name}' received invalid arguments. Repair the payload and retry.",
            errors=pydantic_errors(exc),
        )


def validate_tool_result(tool_name: str, output_model: type[BaseModel] | None, raw: Any) -> tuple[Any | None, ValidationRepairMessage | None]:
    if output_model is None:
        return raw, None
    try:
        if isinstance(raw, BaseModel):
            return output_model.model_validate(raw.model_dump()), None
        return output_model.model_validate(raw), None
    except ValidationError as exc:
        return None, ValidationRepairMessage(
            kind="tool_result",
            message=f"Tool '{tool_name}' returned invalid data. Repair the tool implementation or retry.",
            errors=pydantic_errors(exc),
        )
