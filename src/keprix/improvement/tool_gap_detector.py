"""Detect missing tools from failed runs and user tasks."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.agent.keprix.gap_detector import GapDetector
from keprix.improvement.run_analyzer import ImprovementProposal, RunRecord


@dataclass
class ToolGapProposal:
    proposal_id: str
    tool_name: str
    description: str
    confidence: float


def detect_tool_gaps(record: RunRecord, proposals: list[ImprovementProposal], available_tools: list[str] | None = None) -> list[ToolGapProposal]:
    gaps: list[ToolGapProposal] = []
    detector = GapDetector()
    task = record.metadata.get("task") or record.metadata.get("message") or ""
    if task:
        report = detector.classify(task, available_tools or [])
        if report.has_gap:
            gaps.append(
                ToolGapProposal(
                    proposal_id=proposals[0].proposal_id if proposals else record.run_id,
                    tool_name=report.candidate_tool_name or "generated_tool",
                    description=report.gap_description or "Missing tool capability",
                    confidence=report.confidence,
                )
            )

    for proposal in proposals:
        if proposal.category != "tool_failure":
            continue
        for tool in proposal.metadata.get("tools", []):
            gaps.append(
                ToolGapProposal(
                    proposal_id=proposal.proposal_id,
                    tool_name=str(tool.get("name", "unknown_tool")),
                    description=f"Tool failure: {tool.get('error', 'unknown error')}",
                    confidence=0.8,
                )
            )
    return gaps
