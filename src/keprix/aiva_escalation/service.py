"""Aiva human VA escalation service (K05)."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.aiva_escalation.confidence import estimate_confidence, last_user_input, should_escalate
from keprix.aiva_escalation.config import EscalationConfig, load_escalation_config
from keprix.aiva_escalation.notify import notify_human_vas
from keprix.aiva_escalation.store import EscalationStore, get_escalation_store

ESCALATION_TYPES = ("low_confidence", "out_of_scope", "manual_request", "safety_flag")


class EscalationService:
    def __init__(
        self,
        store: EscalationStore | None = None,
        config: EscalationConfig | None = None,
    ) -> None:
        self.store = store or get_escalation_store()
        self.config = config or load_escalation_config()

    def create(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        original_input: str,
        escalation_type: str = "low_confidence",
        confidence_score: float | None = None,
        session_id: str | None = None,
        holding_message: str | None = None,
        channel: str | None = None,
        notify: bool = True,
    ) -> dict[str, Any]:
        et = (escalation_type or "low_confidence").strip().lower()
        if et not in ESCALATION_TYPES:
            raise ValueError(f"escalation_type must be one of {ESCALATION_TYPES}")
        holding = holding_message or self.config.holding_message_template
        esc = self.store.create_escalation(
            workspace_id=workspace_id,
            worker_id=worker_id,
            session_id=session_id,
            escalation_type=et,
            confidence_score=confidence_score,
            original_input=original_input,
            holding_message=holding,
            channel=channel or ",".join(self.config.notify_channels),
            status="pending",
        )
        notify_log: list[dict[str, Any]] = []
        if notify:
            notify_log = notify_human_vas(esc, self.config)
            self.store.set_notify_log(str(esc["id"]), notify_log)
            esc = self.store.get_escalation(str(esc["id"])) or esc
        try:
            from keprix.aiva_analytics.metrics import record_worker_escalation

            record_worker_escalation(workspace_id, worker_id)
        except Exception:
            pass
        return {"escalation": esc, "notify": notify_log, "holding_message": holding}

    def assign(self, escalation_id: str, assigned_va: str) -> dict[str, Any]:
        row = self.store.assign(escalation_id, assigned_va)
        if not row:
            raise LookupError("escalation_not_found")
        return row

    def complete(
        self,
        escalation_id: str,
        va_response: str,
        *,
        assigned_va: str | None = None,
    ) -> dict[str, Any]:
        if not (va_response or "").strip():
            raise ValueError("va_response is required")
        row = self.store.complete(escalation_id, va_response.strip(), assigned_va=assigned_va)
        if not row:
            raise LookupError("escalation_not_found")
        return row

    def get_queue(
        self,
        workspace_id: str,
        *,
        status: str | None = "pending",
        limit: int = 50,
    ) -> dict[str, Any]:
        items = self.store.list_queue(workspace_id, status=status, limit=limit)
        return {"workspace_id": workspace_id, "status": status, "items": items, "count": len(items)}

    def human_assist_request(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        reason: str,
        urgency: str = "normal",
        details: str | None = None,
        original_input: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        created = self.create(
            workspace_id=workspace_id,
            worker_id=worker_id,
            original_input=original_input or reason,
            escalation_type="manual_request",
            confidence_score=None,
            session_id=session_id,
            notify=True,
        )
        assist = self.store.create_assist_request(
            workspace_id=workspace_id,
            worker_id=worker_id,
            reason=reason,
            urgency=urgency if urgency in ("normal", "urgent") else "normal",
            details=details,
            escalation_id=created["escalation"]["id"],
        )
        return {"assist_request": assist, **created}

    def process_timeouts(self, *, timeout_minutes: int | None = None) -> dict[str, Any]:
        minutes = int(timeout_minutes if timeout_minutes is not None else self.config.timeout_minutes)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        older_than = cutoff.replace(microsecond=0).isoformat()
        reassigned = self.store.reassign_stale(older_than_iso=older_than)
        # Re-notify after timeout
        for row in reassigned:
            notify_human_vas(row, self.config)
        return {"reassigned": len(reassigned), "items": reassigned, "timeout_minutes": minutes}

    def maybe_escalate_turn(
        self,
        *,
        workspace_id: str,
        worker_id: str,
        session_id: str | None,
        messages: list[dict[str, Any]] | None,
        assistant_text: str,
        explicit_confidence: float | None = None,
        force: bool = False,
        escalation_type: str | None = None,
    ) -> dict[str, Any] | None:
        """If confidence is below threshold, create escalation and return holding payload."""
        if not self.config.enabled and not force:
            return None
        confidence = estimate_confidence(
            assistant_text=assistant_text or "",
            original_input=last_user_input(messages),
            explicit=explicit_confidence,
        )
        if not should_escalate(
            confidence,
            self.config.confidence_threshold,
            force=force,
            escalation_type=escalation_type,
        ):
            return None

        original = last_user_input(messages) or "(no user message)"
        et = escalation_type or ("manual_request" if force else "low_confidence")
        created = self.create(
            workspace_id=workspace_id,
            worker_id=worker_id or "default",
            original_input=original,
            escalation_type=et,
            confidence_score=confidence,
            session_id=session_id,
            notify=True,
        )
        return {
            "escalated": True,
            "confidence": confidence,
            "threshold": self.config.confidence_threshold,
            "holding_message": created["holding_message"],
            "escalation": created["escalation"],
            "notify": created["notify"],
        }


_service: EscalationService | None = None
_svc_lock = threading.Lock()


def get_escalation_service(
    store: EscalationStore | None = None,
    config: EscalationConfig | None = None,
) -> EscalationService:
    global _service
    if store is not None or config is not None:
        return EscalationService(store=store, config=config)
    with _svc_lock:
        if _service is None:
            _service = EscalationService()
        return _service


def reset_escalation_service_for_tests(
    store: EscalationStore | None = None,
    config: EscalationConfig | None = None,
) -> EscalationService:
    global _service
    with _svc_lock:
        _service = EscalationService(store=store, config=config)
        return _service
