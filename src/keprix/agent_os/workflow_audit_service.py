"""Workflow audit orchestration (prompt 256)."""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.agent_os.audit_store import AuditStore, AuditTask, WorkflowAuditResult
from keprix.agent_os.interview_agent import interview_reply
from keprix.agent_os.session_scan import scan_sessions


def agent_os_enabled() -> bool:
    return os.environ.get("KEPRIX_AGENT_OS_ENABLED", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "workflow-task"


def normalize_audit_mode(mode: str) -> str:
    normalized = (mode or "").strip().replace("-", "_")
    if normalized not in {"manual", "session_scan", "interview"}:
        raise ValueError(f"Unsupported audit mode: {mode}")
    return normalized


class WorkflowAuditService:
    def __init__(self, store: AuditStore | None = None) -> None:
        self.store = store or AuditStore()

    def start(self, mode: str, user: dict[str, Any], session_count: int = 10) -> WorkflowAuditResult:
        if not agent_os_enabled():
            raise PermissionError("Agent OS is disabled")
        mode = normalize_audit_mode(mode)
        user_id = str(user.get("id") or user.get("user_id") or "")
        audit = self.store.create(mode=mode, user_id=user_id or None)
        if mode == "session_scan":
            tasks, session_ids = scan_sessions(user, session_count=session_count)
            audit.tasks = tasks
            audit.session_ids_scanned = session_ids
        return audit

    def update_manual_tasks(self, audit_id: str, tasks: list[dict[str, Any]]) -> WorkflowAuditResult:
        audit = self._require(audit_id)
        audit.tasks = [
            AuditTask(
                id=item.get("id") or str(uuid.uuid4()),
                domain=item.get("domain") or "general",
                description=item.get("description") or "",
                frequency=item.get("frequency") or "weekly",
                desired_output=item.get("desired_output") or "",
                tools_hint=list(item.get("tools_hint") or []),
                propose_skill=bool(item.get("propose_skill", True)),
                propose_automation=bool(item.get("propose_automation", False)),
            )
            for item in tasks
        ]
        self.store.save(audit)
        return audit

    async def continue_interview(self, audit_id: str, message: str) -> tuple[WorkflowAuditResult, str, bool]:
        audit = self._require(audit_id)
        if audit.mode != "interview":
            raise ValueError("audit is not in interview mode")
        audit.interview_transcript.append({"role": "user", "content": message})
        reply, parsed_tasks = await interview_reply(audit.interview_transcript)
        audit.interview_transcript.append({"role": "assistant", "content": reply})
        done = parsed_tasks is not None
        if parsed_tasks:
            audit.tasks = [
                AuditTask(
                    id=str(uuid.uuid4()),
                    domain=str(item.get("domain") or "general"),
                    description=str(item.get("description") or ""),
                    frequency=str(item.get("frequency") or "weekly"),
                    desired_output=str(item.get("desired_output") or ""),
                    tools_hint=[],
                    propose_skill=bool(item.get("propose_skill", True)),
                    propose_automation=False,
                )
                for item in parsed_tasks
            ]
        self.store.save(audit)
        return audit, reply, done

    def complete(self, audit_id: str) -> WorkflowAuditResult:
        audit = self._require(audit_id)
        audit.proposed_skills = []
        audit.proposed_automations = []
        for task in audit.tasks:
            if not task.description.strip():
                continue
            slug = _slugify(task.description)
            if task.propose_skill:
                audit.proposed_skills.append(
                    {
                        "slug": slug,
                        "name": task.description[:80],
                        "rationale": f"Captured during {audit.mode} workflow audit",
                        "domain": task.domain,
                        "desired_output": task.desired_output,
                        "tools_hint": task.tools_hint,
                    }
                )
            if task.propose_automation:
                audit.proposed_automations.append(
                    {
                        "type": "cron",
                        "name": slug,
                        "skill_slug": slug,
                        "schedule": "0 8 * * 1-5" if task.frequency == "daily" else "0 8 * * 1",
                    }
                )
        audit.status = "completed"
        audit.completed_at = datetime.now(timezone.utc).isoformat()
        self.store.save(audit)
        return audit

    def export_to_proposals(self, audit_id: str) -> int:
        audit = self._require(audit_id)
        if audit.status != "completed":
            audit = self.complete(audit_id)
        proposals = []
        for item in audit.proposed_skills:
            proposals.append(
                {
                    "proposal_id": str(uuid.uuid4()),
                    "source": "audit",
                    "origin": "workflow_audit",
                    "audit_id": audit.audit_id,
                    "status": "pending",
                    "description": item.get("name") or item.get("slug") or "Workflow audit skill",
                    "evidence_sessions": audit.session_ids_scanned,
                    **item,
                }
            )
        return self.store.append_proposals_queue(proposals)

    def get(self, audit_id: str) -> WorkflowAuditResult | None:
        return self.store.load(audit_id)

    def list_audits(self, user: dict[str, Any]) -> list[WorkflowAuditResult]:
        user_id = str(user.get("id") or user.get("user_id") or "")
        return self.store.list_audits(user_id=user_id or None)

    def _require(self, audit_id: str) -> WorkflowAuditResult:
        audit = self.store.load(audit_id)
        if audit is None:
            raise KeyError(audit_id)
        return audit
