"""Mutation engine type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GapReport:
    has_gap: bool
    gap_description: str = ""
    candidate_tool_name: str = ""
    candidate_approach: str = ""
    confidence: float = 0.0
    task: str = ""


@dataclass
class SynthesisResult:
    tool_name: str
    tool_code: str
    skill_yaml: str
    description: str
    test_input: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    safe: bool
    violations: list[str] = field(default_factory=list)
    severity: str = "block"


@dataclass
class SandboxResult:
    passed: bool
    output: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0
    memory_mb: float = 0.0
    mode: str = "local"


@dataclass
class GeneratedToolRecord:
    id: str
    task_that_triggered: str
    tool_name: str
    tool_code: str
    skill_yaml: str
    description: str
    gap_description: str
    static_analysis: dict[str, Any]
    sandbox_result: dict[str, Any]
    status: str = "pending"
    approver_id: str | None = None
    approver_channel: str | None = None
    rejection_reason: str | None = None
    approved_at: str | None = None
    rejected_at: str | None = None
    installed_at: str | None = None
    created_at: str | None = None
    channel_approvals: dict[str, bool] | None = None
    channel_rejections: dict[str, str] | None = None
    signature: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class ApprovalResult:
    record: GeneratedToolRecord
    retry_message: str | None = None
