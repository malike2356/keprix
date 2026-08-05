"""Tests for tool call auditing."""

from __future__ import annotations

from agent.tool_audit import ToolCallAuditor, ToolResult
from agent.tool_schema import ParameterSchema, ToolSchema
from agent.transports.types import build_tool_call


def _schema() -> ToolSchema:
    return ToolSchema(
        name="pay",
        description="Create payment",
        parameters={
            "amount": ParameterSchema(name="amount", type="number", description="Minor units"),
            "currency": ParameterSchema(
                name="currency",
                type="string",
                description="ISO code",
                enum=["gbp", "usd"],
            ),
        },
    )


def test_validate_call_flags_missing_and_unknown_parameters():
    auditor = ToolCallAuditor()
    call = build_tool_call("c1", "pay", {"currency": "eur", "extra": 1})
    result = auditor.validate_call(call, _schema())
    assert result.valid is False
    assert any("Missing required parameter: amount" in err for err in result.errors)
    assert any("Invalid value for currency" in err for err in result.errors)
    assert any("Unknown parameter: extra" in err for err in result.errors)


def test_track_quality_records_audit():
    auditor = ToolCallAuditor()
    call = build_tool_call("c1", "pay", {"amount": 100, "currency": "gbp"})
    audit = auditor.validate_call(call, _schema())
    auditor.track_quality(call, ToolResult(success=True), audit)
    assert auditor.quality_log[-1]["tool"] == "pay"
    assert auditor.quality_log[-1]["valid"] is True
