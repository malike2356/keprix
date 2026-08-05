"""Tool call schema validation and quality tracking."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from agent.tool_schema import ToolSchema
from agent.transports.types import ToolCall

logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ToolResult:
    success: bool
    content: str = ""
    error: str | None = None


class ToolCallAuditor:
    """Validates tool calls against schemas and tracks quality signals."""

    def __init__(self) -> None:
        self._quality_log: list[dict[str, Any]] = []

    def validate_call(self, call: ToolCall, schema: ToolSchema) -> AuditResult:
        parameters = self._parameters_from_call(call)
        errors: list[str] = []

        for name, param in schema.parameters.items():
            if param.required and name not in parameters:
                errors.append(f"Missing required parameter: {name}")
            if name in parameters and param.enum:
                value = parameters[name]
                if value not in param.enum:
                    errors.append(
                        f"Invalid value for {name}: {value!r}. "
                        f"Must be one of: {param.enum}"
                    )

        for name in parameters:
            if name not in schema.parameters:
                errors.append(
                    f"Unknown parameter: {name}. Schema has: "
                    f"{list(schema.parameters.keys())}"
                )

        warnings = self._check_best_practices(parameters, schema)
        return AuditResult(valid=not errors, errors=errors, warnings=warnings)

    def track_quality(self, call: ToolCall, result: ToolResult, audit: AuditResult) -> None:
        entry = {
            "tool": call.name,
            "valid": audit.valid,
            "success": result.success,
            "errors": list(audit.errors),
            "warnings": list(audit.warnings),
        }
        self._quality_log.append(entry)
        if audit.errors:
            logger.warning("Tool call audit failed for %s: %s", call.name, "; ".join(audit.errors))
        elif audit.warnings:
            logger.info("Tool call audit warnings for %s: %s", call.name, "; ".join(audit.warnings))

    @property
    def quality_log(self) -> list[dict[str, Any]]:
        return list(self._quality_log)

    def _parameters_from_call(self, call: ToolCall) -> dict[str, Any]:
        raw = call.arguments
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _check_best_practices(self, parameters: dict[str, Any], schema: ToolSchema) -> list[str]:
        warnings: list[str] = []
        if schema.examples and not parameters:
            warnings.append("No parameters provided; an example call exists in the schema.")
        return warnings
