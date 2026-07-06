"""Mutation cycle orchestration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from keprix.agent.keprix.approval import ApprovalWorkflow
from keprix.agent.keprix.auditor import MutationAuditor
from keprix.agent.keprix.config import get_mutation_config
from keprix.agent.keprix.gap_detector import GapDetector
from keprix.agent.keprix.sandbox import SandboxRunner
from keprix.agent.keprix.schemas import ApprovalResult, GeneratedToolRecord, GapReport
from keprix.agent.keprix.static_analyser import static_analyser
from keprix.agent.keprix.synthesiser import ToolSynthesiser
from keprix.agent.keprix.store import get_generated_tool_store


class MutationEngine:
    def __init__(self) -> None:
        self._gap = GapDetector()
        self._synthesiser = ToolSynthesiser()
        self._sandbox = SandboxRunner()
        self._auditor = MutationAuditor()
        self._approval = ApprovalWorkflow()

    def detect_gap(self, task: str, available_tools: list[str]) -> GapReport:
        return self._gap.classify(task, available_tools)

    async def detect_gap_async(self, task: str, available_tools: list[str]) -> GapReport:
        return await self._gap.classify_async(task, available_tools)

    async def run_cycle(
        self,
        task: str,
        available_tools: list[str],
        *,
        session_id: str | None = None,
        trigger: str = "gap",
        requested_tool: str | None = None,
    ) -> dict[str, Any]:
        config = get_mutation_config()
        if not config.enabled:
            return {"started": False, "reason": "mutation_disabled"}

        gap = await self.detect_gap_async(task, available_tools)
        if not gap.has_gap:
            return {"started": False, "reason": "no_gap", "gap": asdict(gap)}

        rewrite_hint: str | None = None
        synthesis = None
        analysis = None
        for attempt in range(config.max_retries + 1):
            synthesis = await self._synthesiser.synthesise(gap, rewrite_hint=rewrite_hint)
            analysis = static_analyser.scan(synthesis.tool_code)
            if analysis.safe:
                break
            rewrite_hint = "; ".join(analysis.violations)

        if synthesis is None or analysis is None or not analysis.safe:
            return {
                "started": True,
                "status": "blocked",
                "violations": analysis.violations if analysis else [],
            }

        sandbox = await self._sandbox.run(
            synthesis.tool_code,
            synthesis.test_input,
            synthesis.tool_name,
        )
        record = self._auditor.record_synthesis(
            task_that_triggered=task,
            tool_name=synthesis.tool_name,
            tool_code=synthesis.tool_code,
            skill_yaml=synthesis.skill_yaml,
            description=synthesis.description,
            gap_description=gap.gap_description,
            static_analysis=asdict(analysis),
            sandbox_result=asdict(sandbox),
            session_id=session_id,
            metadata={
                "original_task": task,
                "session_id": session_id,
                "trigger": trigger,
                "requested_tool": requested_tool,
            },
        )
        await self._approval.register_pending(record)
        return {
            "started": True,
            "status": "pending_approval" if config.require_approval else "synthesised",
            "record_id": record.id,
            "tool_name": record.tool_name,
            "sandbox_passed": sandbox.passed,
            "message": self._status_message(record, sandbox.passed),
            "record": asdict(record),
        }

    async def approve(self, record_id: str, *, approver_id: str, channel: str = "web") -> ApprovalResult | None:
        return await self._approval.approve(record_id, approver_id=approver_id, channel=channel)

    async def reject(self, record_id: str, *, approver_id: str, reason: str | None = None, channel: str = "web") -> GeneratedToolRecord | None:
        return await self._approval.reject(record_id, approver_id=approver_id, reason=reason, channel=channel)

    def list_pending(self) -> list[GeneratedToolRecord]:
        return get_generated_tool_store().list_all(status="pending")

    def _status_message(self, record: GeneratedToolRecord, sandbox_passed: bool) -> str:
        status = "PASSED" if sandbox_passed else "FAILED"
        return (
            f"I don't have a tool that can handle this yet. Creating tool: {record.tool_name}.\n"
            f"Sandbox test: {status}.\n"
            "Awaiting your approval."
        )


_engine: MutationEngine | None = None


def get_mutation_engine() -> MutationEngine:
    global _engine
    if _engine is None:
        _engine = MutationEngine()
    return _engine
