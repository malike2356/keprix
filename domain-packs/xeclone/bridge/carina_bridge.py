"""Carina bridge helpers for draft handoff into existing approval UI."""

from __future__ import annotations

import uuid
from typing import Any

from approvals.service import submit_preview
from bridge.dual_run import bridge_envelope, circuit_open, fallback_to_carina
from persona.binding import persona_version
from scout.events import emit_scout_event


def handoff_draft_to_approval(
    *,
    content: str,
    channel: str,
    audience: str,
    tenant: str,
    worker_id: str,
    correlation_id: str,
    private_reply: bool = False,
    already_emitted: bool = False,
) -> dict[str, Any]:
    """Keprix draft enters approval without changing live inbound path."""
    if circuit_open():
        return fallback_to_carina(action="draft_approval", already_emitted=already_emitted)

    version = persona_version()
    approval = submit_preview(
        content=content,
        channel=channel,
        audience=audience,
        persona_version=version,
        private_reply=private_reply,
    )
    run_id = f"krun_{uuid.uuid4().hex[:12]}"
    envelope = bridge_envelope(
        worker_id=worker_id,
        persona_version=version,
        approval_id=approval["approval_id"],
        keprix_run_id=run_id,
        tenant=tenant,
        correlation_id=correlation_id,
    )
    emit_scout_event(
        "approval",
        {
            "approval_id": approval["approval_id"],
            "content_hash": approval["content_hash"],
            "tenant_id": tenant,
            "inbound_path_changed": False,
        },
    )
    return {
        "ok": True,
        "approval": approval,
        "bridge": envelope,
        "inbound_path": "carina_unchanged",
        "wave": 1,
    }
