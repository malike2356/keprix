"""Approval workflow helpers."""

from __future__ import annotations

from keprix.agent.keprix.approval_gate import (
    clear_pending,
    get_pending,
    normalize_channel,
    record_decision,
    required_channels,
    submit_for_approval,
)
from keprix.agent.keprix.auditor import MutationAuditor
from keprix.agent.keprix.installer import LiveInstaller
from keprix.agent.keprix.retry import KeprixRetry
from keprix.agent.keprix.schemas import ApprovalResult, GeneratedToolRecord
from keprix.agent.keprix.store import get_generated_tool_store


class ApprovalWorkflow:
    def __init__(self) -> None:
        self._store = get_generated_tool_store()
        self._auditor = MutationAuditor(self._store)
        self._installer = LiveInstaller()
        self._retry = KeprixRetry()

    async def register_pending(self, record: GeneratedToolRecord) -> str:
        await submit_for_approval(
            record.tool_name,
            record.tool_code,
            request_id=record.id,
        )
        return record.id

    async def approve(self, record_id: str, *, approver_id: str, channel: str = "web") -> ApprovalResult | None:
        record = self._store.get(record_id)
        if record is None or record.status not in {"pending", "approved"}:
            return None

        pending = get_pending(record_id)
        if pending is None:
            await submit_for_approval(record.tool_name, record.tool_code, request_id=record_id)

        gate = await record_decision(record_id, channel, approved=True)
        if gate is None:
            return None
        if gate.is_rejected():
            rejected = self._auditor.mark_rejected(
                record_id,
                approver_id=approver_id,
                channel=channel,
                reason="rejected in gate",
            )
            if rejected is None:
                return None
            return ApprovalResult(record=rejected, retry_message=None)

        channel_approvals = dict(record.channel_approvals or {})
        channel_approvals.update(gate.channel_approvals)
        self._store.update(record_id, channel_approvals=channel_approvals, status="pending")

        if not gate.is_approved(required_channels()):
            updated = self._store.get(record_id)
            if updated is None:
                return None
            return ApprovalResult(record=updated, retry_message=None)

        approved = self._auditor.mark_approved(record_id, approver_id=approver_id, channel=normalize_channel(channel))
        if approved is None:
            return None
        installed = await self._installer.install(approved)
        if not installed:
            return ApprovalResult(record=approved, retry_message=None)
        installed_record = self._auditor.mark_installed(record_id)
        clear_pending(record_id)
        if installed_record is None:
            return ApprovalResult(record=approved, retry_message=None)

        metadata = installed_record.metadata or {}
        original_task = str(metadata.get("original_task") or installed_record.task_that_triggered)
        session_id = installed_record.session_id or metadata.get("session_id")
        retry_message = await self._retry.retry(
            original_message=original_task,
            tool_name=installed_record.tool_name,
            session_id=str(session_id) if session_id else None,
        )
        return ApprovalResult(record=installed_record, retry_message=retry_message)

    async def reject(self, record_id: str, *, approver_id: str, channel: str = "web", reason: str | None = None) -> GeneratedToolRecord | None:
        record = self._store.get(record_id)
        if record is None or record.status != "pending":
            return None
        await record_decision(record_id, channel, approved=False, reason=reason or "rejected")
        clear_pending(record_id)
        return self._auditor.mark_rejected(record_id, approver_id=approver_id, channel=channel, reason=reason)
