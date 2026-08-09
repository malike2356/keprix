"""Outreach automation service (campaigns, sequences, due processing, replies)."""

from __future__ import annotations

import csv
import io
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from keprix.outreach.classify import (
    classify_reply_sync,
    enrollment_stop_status,
    lead_status_for_classification,
)
from keprix.outreach.store import OutreachStore, get_outreach_store

logger = logging.getLogger(__name__)

PIPELINE_STAGES = (
    "new",
    "enrolled",
    "contacted",
    "replied",
    "interested",
    "booking",
    "booked",
    "won",
    "lost",
    "not_now",
    "unsubscribed",
    "follow_up",
    "attended",
    "ghosted",
    "proposal_sent",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _in_business_hours(tz_name: str, now: datetime | None = None) -> bool:
    try:
        tz = ZoneInfo(tz_name or "Europe/London")
    except Exception:
        tz = ZoneInfo("Europe/London")
    local = (now or _utcnow()).astimezone(tz)
    if local.weekday() >= 5:
        return False
    return 9 <= local.hour < 17


def _render_template(text: str, lead: dict[str, Any], campaign: dict[str, Any] | None = None) -> str:
    booking = (campaign or {}).get("default_booking_link") or ""
    if not booking and campaign:
        try:
            from keprix.crm.booking import resolve_booking_link
            import json as _json

            meta = {}
            raw = lead.get("metadata_json") or lead.get("notes")
            if isinstance(raw, str) and raw.strip().startswith("{"):
                try:
                    parsed = _json.loads(raw)
                    meta = parsed.get("crm") if isinstance(parsed.get("crm"), dict) else parsed
                except Exception:
                    meta = {}
            link = resolve_booking_link(
                host_user_id=str(campaign.get("host_user_id") or lead.get("workspace_id") or ""),
                event_type_id=campaign.get("vical_event_type_id"),
                campaign=campaign,
                crm_lead_id=(meta or {}).get("crm_lead_id"),
                crm_contact_id=(meta or {}).get("crm_contact_id"),
            )
            booking = str(link.get("book_url") or link.get("fallback_link") or "")
        except Exception:
            pass
    replacements = {
        "{{first_name}}": lead.get("first_name") or "",
        "{{last_name}}": lead.get("last_name") or "",
        "{{email}}": lead.get("email") or "",
        "{{company}}": lead.get("company") or "",
        "{{booking_link}}": booking,
    }
    out = text or ""
    for key, val in replacements.items():
        out = out.replace(key, str(val))
    return out


def _parse_leads_csv(csv_text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    leads: list[dict[str, Any]] = []
    for row in reader:
        email = (row.get("email") or row.get("Email") or "").strip()
        if not email:
            continue
        leads.append(
            {
                "email": email,
                "first_name": (row.get("first_name") or row.get("firstName") or "").strip() or None,
                "last_name": (row.get("last_name") or row.get("lastName") or "").strip() or None,
                "company": (row.get("company") or "").strip() or None,
                "phone": (row.get("phone") or "").strip() or None,
                "source": (row.get("source") or "csv_import").strip() or "csv_import",
                "tags": row.get("tags"),
                "notes": row.get("notes"),
            }
        )
    return leads


class OutreachService:
    def __init__(self, store: OutreachStore | None = None) -> None:
        self.store = store or get_outreach_store()

    def create_campaign(self, workspace_id: str, name: str, **fields: Any) -> dict[str, Any]:
        return self.store.create_campaign(workspace_id, name, **fields)

    def update_campaign(self, workspace_id: str, campaign_id: str, **fields: Any) -> dict[str, Any] | None:
        return self.store.update_campaign(workspace_id, campaign_id, **fields)

    def create_sequence(
        self,
        workspace_id: str,
        name: str,
        steps: list[dict[str, Any]] | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        if steps is not None and len(steps) < 1:
            raise ValueError("sequence requires at least one step")
        return self.store.create_sequence(workspace_id, name, steps=steps, **fields)

    def add_leads(
        self,
        workspace_id: str,
        *,
        leads: list[dict[str, Any]] | None = None,
        csv_text: str | None = None,
        campaign_id: str | None = None,
    ) -> dict[str, Any]:
        batch = list(leads or [])
        if csv_text:
            batch.extend(_parse_leads_csv(csv_text))
        created = self.store.add_leads(workspace_id, batch, campaign_id=campaign_id)
        return {"created": len(created), "leads": created}

    def enroll_lead(
        self,
        workspace_id: str,
        lead_id: str,
        sequence_id: str,
        *,
        start_immediately: bool = True,
    ) -> dict[str, Any]:
        lead = self.store.get_lead(workspace_id, lead_id)
        if not lead:
            raise LookupError("lead_not_found")
        seq = self.store.get_sequence(workspace_id, sequence_id)
        if not seq:
            raise LookupError("sequence_not_found")
        next_run = _iso(_utcnow()) if start_immediately else _iso(_utcnow() + timedelta(hours=1))
        enrollment = self.store.enroll_lead(
            lead_id, sequence_id, workspace_id=workspace_id, next_run_at=next_run
        )
        self.store.update_lead_status(workspace_id, lead_id, "enrolled")
        return {"enrollment": enrollment, "lead": self.store.get_lead(workspace_id, lead_id)}

    def move_lead(self, workspace_id: str, lead_id: str, status: str) -> dict[str, Any]:
        if status not in PIPELINE_STAGES:
            raise ValueError(f"invalid status; expected one of {PIPELINE_STAGES}")
        lead = self.store.update_lead_status(workspace_id, lead_id, status)
        if not lead:
            raise LookupError("lead_not_found")
        return lead

    def get_pipeline(self, workspace_id: str, campaign_id: str | None = None) -> dict[str, Any]:
        counts = self.store.pipeline_counts(workspace_id, campaign_id)
        board = {stage: counts.get(stage, 0) for stage in PIPELINE_STAGES}
        for status, count in counts.items():
            if status not in board:
                board[status] = count
        return {
            "workspace_id": workspace_id,
            "campaign_id": campaign_id,
            "stages": board,
            "total": sum(board.values()),
        }

    def get_campaign_stats(self, workspace_id: str, campaign_id: str) -> dict[str, Any]:
        return self.store.campaign_stats(workspace_id, campaign_id)

    def _send_message(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        dry_run: bool,
    ) -> dict[str, Any]:
        if dry_run or os.environ.get("KEPRIX_OUTREACH_DRY_RUN", "1") not in ("0", "false", "False"):
            return {"sent": True, "dry_run": True, "to": to_email}
        try:
            # Optional live SMTP when explicitly enabled and account helpers exist
            from keprix.email.helpers import send_smtp_message  # noqa: F401

            logger.info("outreach live send requested to %s (subject=%s)", to_email, subject[:80])
            # Without a configured account binding, keep dry_run semantics
            return {"sent": True, "dry_run": True, "to": to_email, "note": "no_account_bound"}
        except Exception as exc:
            return {"sent": False, "dry_run": True, "error": str(exc), "to": to_email}

    def revalidate_enrollment_send(
        self,
        enrollment: dict[str, Any],
        *,
        now: datetime | None = None,
        defer_outside_hours: bool = True,
        defer_daily_cap: bool = True,
    ) -> dict[str, Any]:
        """Return {ok: True, ...ctx} or {ok: False, reason, stop?, defer_until?}."""
        from keprix.outreach.ops import get_outreach_ops_store
        from keprix.outreach.scheduler import next_midnight_in_tz, next_open_business_window

        now_dt = now or _utcnow()
        lead_id = str(enrollment["lead_id"])
        lead_row = self.store._fetchone("SELECT * FROM outreach_leads WHERE id = ?", (lead_id,))
        if not lead_row:
            return {"ok": False, "reason": "lead_missing", "stop": False}
        ws = str(lead_row["workspace_id"])
        ops = get_outreach_ops_store()
        control = ops.get_control(ws)
        if control.get("paused"):
            return {"ok": False, "reason": "outreach_paused", "stop": False, "workspace_id": ws}

        campaign = None
        if lead_row.get("campaign_id"):
            campaign = self.store.get_campaign(ws, str(lead_row["campaign_id"]))
            if campaign and campaign.get("status") in ("paused", "archived", "stopped"):
                return {
                    "ok": False,
                    "reason": "campaign_not_active",
                    "stop": False,
                    "workspace_id": ws,
                    "lead": lead_row,
                    "campaign": campaign,
                }

        try:
            from keprix.crm.store import get_crm_store

            cstore = get_crm_store()
            if cstore.is_kill_switch_on(ws, scope="workspace"):
                return {"ok": False, "reason": "workspace_kill_switch", "stop": False, "workspace_id": ws}
            email = str(lead_row.get("email") or "").strip().lower()
            if email and cstore.is_suppressed(ws, channel="email", address=email):
                return {
                    "ok": False,
                    "reason": "crm_suppressed",
                    "stop": True,
                    "stop_status": "stopped_suppressed",
                    "workspace_id": ws,
                    "lead": lead_row,
                    "campaign": campaign,
                }
            from keprix.crm.nurture import cadence_allows_send

            ok_cadence, cadence_reason = cadence_allows_send(
                ws, email, crm_store=cstore, outreach_store=self.store, now=now_dt
            )
            if not ok_cadence:
                return {
                    "ok": False,
                    "reason": cadence_reason or "cadence_cap",
                    "stop": False,
                    "workspace_id": ws,
                    "lead": lead_row,
                    "campaign": campaign,
                }
        except Exception:
            pass

        sequence = self.store.get_sequence(ws, str(enrollment["sequence_id"]))
        if not sequence:
            return {"ok": False, "reason": "sequence_missing", "stop": False, "workspace_id": ws}

        # stop_on_reply / booking / unsubscribe via lead status
        lead_status = str(lead_row.get("status") or "")
        if sequence.get("stop_on_unsubscribe") and lead_status == "unsubscribed":
            return {
                "ok": False,
                "reason": "unsubscribed",
                "stop": True,
                "stop_status": "stopped_unsubscribe",
                "workspace_id": ws,
                "lead": lead_row,
                "campaign": campaign,
                "sequence": sequence,
            }
        if sequence.get("stop_on_reply") and lead_status in ("replied", "interested"):
            return {
                "ok": False,
                "reason": "already_replied",
                "stop": True,
                "stop_status": "stopped_reply",
                "workspace_id": ws,
                "lead": lead_row,
                "campaign": campaign,
                "sequence": sequence,
            }
        if sequence.get("stop_on_booking") and lead_status in ("booking", "booked", "attended"):
            return {
                "ok": False,
                "reason": "already_booked",
                "stop": True,
                "stop_status": "stopped_booking",
                "workspace_id": ws,
                "lead": lead_row,
                "campaign": campaign,
                "sequence": sequence,
            }

        tz_name = str((campaign or {}).get("timezone") or "Europe/London")
        if (
            defer_outside_hours
            and campaign
            and campaign.get("business_hours_only")
            and not _in_business_hours(tz_name, now_dt)
        ):
            return {
                "ok": False,
                "reason": "outside_business_hours",
                "stop": False,
                "defer_until": _iso(next_open_business_window(tz_name, now_dt)),
                "workspace_id": ws,
                "lead": lead_row,
                "campaign": campaign,
                "sequence": sequence,
            }

        if defer_daily_cap and campaign:
            day_prefix = now_dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
            sent_today = self.store.count_messages_sent_today(str(campaign["id"]), day_prefix)
            if sent_today >= int(campaign.get("daily_cap") or 50):
                return {
                    "ok": False,
                    "reason": "daily_cap",
                    "stop": False,
                    "defer_until": _iso(next_midnight_in_tz(tz_name, now_dt)),
                    "workspace_id": ws,
                    "lead": lead_row,
                    "campaign": campaign,
                    "sequence": sequence,
                }

        steps = sequence.get("steps") or []
        step_index = int(enrollment.get("current_step") or 0)
        if step_index >= len(steps):
            return {
                "ok": False,
                "reason": "completed",
                "stop": True,
                "stop_status": "completed",
                "workspace_id": ws,
                "lead": lead_row,
                "campaign": campaign,
                "sequence": sequence,
            }

        return {
            "ok": True,
            "workspace_id": ws,
            "lead": lead_row,
            "campaign": campaign,
            "sequence": sequence,
            "step": steps[step_index],
            "step_index": step_index,
            "steps": steps,
        }

    def process_due(
        self,
        workspace_id: str | None = None,
        *,
        limit: int = 50,
        now: datetime | None = None,
        dry_run: bool | None = None,
        worker_id: str | None = None,
        lease_seconds: int = 60,
        max_attempts: int | None = None,
    ) -> dict[str, Any]:
        from keprix.outreach.ops import get_outreach_ops_store
        from keprix.outreach.scheduler import backoff_seconds, DEFAULT_MAX_ATTEMPTS

        now_dt = now or _utcnow()
        now_iso = _iso(now_dt)
        dry = True if dry_run is None else dry_run
        soft_wall_default = os.environ.get("KEPRIX_OUTREACH_SOFT_WALL", "1") not in ("0", "false", "False")
        ops = get_outreach_ops_store()
        worker = str(worker_id or f"worker-{uuid.uuid4().hex[:8]}")
        max_att = int(max_attempts if max_attempts is not None else os.environ.get("KEPRIX_OUTREACH_MAX_ATTEMPTS") or DEFAULT_MAX_ATTEMPTS)

        claimed = self.store.claim_due_enrollments(
            now_iso=now_iso,
            limit=limit,
            worker_id=worker,
            lease_seconds=lease_seconds,
            workspace_id=workspace_id,
        )
        processed: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []

        for enrollment in claimed:
            eid = str(enrollment["id"])
            try:
                gate = self.revalidate_enrollment_send(enrollment, now=now_dt)
                if not gate.get("ok"):
                    reason = str(gate.get("reason") or "ineligible")
                    if gate.get("stop"):
                        self.store.update_enrollment(
                            eid,
                            status=str(gate.get("stop_status") or "cancelled"),
                            next_run_at=None,
                            locked_until=None,
                            locked_by=None,
                        )
                    elif gate.get("defer_until"):
                        self.store.update_enrollment(
                            eid,
                            next_run_at=str(gate["defer_until"]),
                            locked_until=None,
                            locked_by=None,
                        )
                    else:
                        # pause / campaign inactive: release lock, keep due for later
                        self.store.release_enrollment_lock(eid, worker)
                    skipped.append({"enrollment_id": eid, "reason": reason})
                    continue

                if workspace_id and gate["workspace_id"] != workspace_id:
                    self.store.release_enrollment_lock(eid, worker)
                    continue

                ws = str(gate["workspace_id"])
                lead_row = gate["lead"]
                campaign = gate.get("campaign")
                sequence = gate["sequence"]
                step = gate["step"]
                step_index = int(gate["step_index"])
                steps = gate["steps"]
                step_order = int(step.get("step_order") or (step_index + 1))

                subject = _render_template(str(step.get("subject") or ""), lead_row, campaign)
                body = _render_template(str(step.get("body") or ""), lead_row, campaign)
                if step.get("cta"):
                    body = f"{body}\n\n{step['cta']}"
                if step.get("link"):
                    body = f"{body}\n{step['link']}"

                require_approval = soft_wall_default or bool((campaign or {}).get("require_approval"))
                use_soft_wall = require_approval and not dry
                idem_key = f"enrollment:{eid}:step:{step_order}"

                message = self.store.create_message(
                    enrollment_id=eid,
                    workspace_id=ws,
                    step_id=step.get("id"),
                    step_order=step_order,
                    channel=step.get("channel") or "email",
                    subject=subject,
                    body=body,
                    sent_at=None,
                    idempotency_key=idem_key,
                )

                send_result: dict[str, Any]
                approval = None
                action = "queued"

                if dry:
                    send_result = {"sent": False, "dry_run": True, "to": lead_row["email"]}
                    action = "dry_run_queued"
                    self._advance_enrollment_after_step(
                        enrollment_id=eid,
                        step_index=step_index,
                        steps=steps,
                        step=step,
                        now_dt=now_dt,
                        clear_attempts=True,
                    )
                elif use_soft_wall:
                    approval = ops.create_approval(
                        ws,
                        message_id=message.get("id"),
                        enrollment_id=eid,
                        lead_id=str(lead_row["id"]),
                        recipient=str(lead_row["email"]),
                        subject=subject,
                        draft_body=body,
                        campaign_id=str(lead_row.get("campaign_id") or (campaign or {}).get("id") or "") or None,
                    )
                    send_result = {
                        "sent": False,
                        "soft_wall": True,
                        "approval_id": approval.get("id"),
                        "to": lead_row["email"],
                    }
                    action = "soft_wall_queued"
                    # Park: do NOT advance current_step
                    self.store.update_enrollment(
                        eid,
                        status="awaiting_approval",
                        next_run_at=None,
                        locked_until=None,
                        locked_by=None,
                    )
                else:
                    send_result = self._send_message(
                        to_email=str(lead_row["email"]),
                        subject=subject,
                        body=body,
                        dry_run=False,
                    )
                    if send_result.get("sent"):
                        self.store._conn.execute(
                            "UPDATE outreach_messages SET sent_at = ?, approval_status = 'none' WHERE id = ?",
                            (now_iso, message["id"]),
                        )
                        self.store._conn.commit()
                        action = "sent_step"
                        self._advance_enrollment_after_step(
                            enrollment_id=eid,
                            step_index=step_index,
                            steps=steps,
                            step=step,
                            now_dt=now_dt,
                            clear_attempts=True,
                        )
                    else:
                        action = "send_failed"
                        attempts = int(enrollment.get("attempt_count") or 0) + 1
                        err = str(send_result.get("error") or "send_failed")
                        permanent = bool(send_result.get("permanent"))
                        if permanent or attempts >= max_att:
                            self.store.update_enrollment(
                                eid,
                                status="dead_letter",
                                next_run_at=None,
                                attempt_count=attempts,
                                last_error=err,
                                dead_letter_at=now_iso,
                                locked_until=None,
                                locked_by=None,
                            )
                            action = "dead_letter"
                        else:
                            delay = backoff_seconds(attempts)
                            self.store.update_enrollment(
                                eid,
                                status="active",
                                next_run_at=_iso(now_dt + timedelta(seconds=delay)),
                                attempt_count=attempts,
                                last_error=err,
                                locked_until=None,
                                locked_by=None,
                            )
                            action = "retry_backoff"

                if lead_row.get("status") in ("new", "enrolled") and action not in (
                    "send_failed",
                    "retry_backoff",
                    "dead_letter",
                ):
                    self.store.update_lead_status(ws, str(lead_row["id"]), "contacted")

                if send_result.get("sent"):
                    try:
                        from keprix.aiva_analytics.metrics import record_outreach_email_sent

                        record_outreach_email_sent(
                            ws,
                            campaign_id=str(lead_row.get("campaign_id") or (campaign or {}).get("id") or ""),
                        )
                    except Exception:
                        pass

                # Ensure lock cleared when advance path already cleared it; no-op otherwise
                self.store.release_enrollment_lock(eid, worker)

                if action == "dry_run_queued":
                    action = "sent_final" if int(gate["step_index"]) + 1 >= len(steps) else "sent_step"
                elif action.startswith("sent") and int(gate["step_index"]) + 1 >= len(steps):
                    action = "sent_final"

                processed.append(
                    {
                        "enrollment_id": eid,
                        "lead_id": str(lead_row["id"]),
                        "step_order": step_order,
                        "message_id": message.get("id"),
                        "approval_id": (approval or {}).get("id"),
                        "action": action,
                        "send": send_result,
                        "idempotency_key": idem_key,
                    }
                )
            except Exception as exc:
                logger.exception("scheduler tick failed for enrollment %s", eid)
                try:
                    self.store.release_enrollment_lock(eid, worker)
                except Exception:
                    pass
                skipped.append({"enrollment_id": eid, "reason": f"tick_error:{exc}"})

        try:
            depth = int(
                (self.store.get_scheduler_health(workspace_id) or {}).get("queue_depth") or 0
            )
            self.store.record_scheduler_heartbeat(
                workspace_id=str(workspace_id or ""),
                worker_id=worker,
                queue_depth=depth,
                metadata={"processed": len(processed), "skipped": len(skipped)},
                now_iso=now_iso,
            )
        except Exception:
            pass

        return {
            "processed": len(processed),
            "skipped": len(skipped),
            "items": processed,
            "skipped_items": skipped,
            "at": now_iso,
            "soft_wall": soft_wall_default,
            "worker_id": worker,
            "claimed": len(claimed),
        }

    def _advance_enrollment_after_step(
        self,
        *,
        enrollment_id: str,
        step_index: int,
        steps: list[dict[str, Any]],
        step: dict[str, Any],
        now_dt: datetime,
        clear_attempts: bool = False,
    ) -> None:
        next_step = step_index + 1
        fields: dict[str, Any] = {
            "locked_until": None,
            "locked_by": None,
        }
        if clear_attempts:
            fields["attempt_count"] = 0
            fields["last_error"] = None
        if next_step >= len(steps):
            fields.update(current_step=next_step, status="completed", next_run_at=None)
        else:
            delay_hours = int(step.get("delay_hours") or 24)
            fields.update(
                current_step=next_step,
                next_run_at=_iso(now_dt + timedelta(hours=delay_hours)),
                status="active",
            )
        self.store.update_enrollment(enrollment_id, **fields)

    def approve_soft_wall(
        self,
        workspace_id: str,
        approval_id: str,
        *,
        now: datetime | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Revalidate then approve Soft Wall draft; advance enrollment only if eligible."""
        from keprix.outreach.ops import get_outreach_ops_store

        ops = get_outreach_ops_store()
        now_dt = now or _utcnow()
        now_iso = _iso(now_dt)
        approval = None
        for row in ops.list_approvals(workspace_id, status="pending"):
            if row.get("id") == approval_id:
                approval = row
                break
        if not approval:
            # also allow already-fetched
            all_rows = ops.list_approvals(workspace_id, status="")
            approval = next((r for r in all_rows if r.get("id") == approval_id), None)
        if not approval:
            raise LookupError("approval_not_found")
        if approval.get("status") != "pending":
            return {"ok": False, "reason": "not_pending", "approval": approval}

        enrollment_id = approval.get("enrollment_id")
        enrollment = self.store.get_enrollment(str(enrollment_id), workspace_id=workspace_id) if enrollment_id else None
        if not enrollment:
            ops.resolve_approval(workspace_id, approval_id, "rejected")
            return {"ok": False, "reason": "enrollment_missing", "approval": approval}

        # Temporarily treat awaiting_approval as active for revalidation of stop rules
        probe = {**enrollment, "status": "active"}
        gate = self.revalidate_enrollment_send(
            probe, now=now_dt, defer_outside_hours=False, defer_daily_cap=True
        )
        if not gate.get("ok"):
            reason = str(gate.get("reason") or "ineligible")
            if gate.get("defer_until"):
                self.store.update_enrollment(
                    str(enrollment_id),
                    status="active",
                    next_run_at=str(gate["defer_until"]),
                    locked_until=None,
                    locked_by=None,
                )
                return {"ok": False, "reason": reason, "deferred": True, "approval": approval}
            if gate.get("stop"):
                self.store.update_enrollment(
                    str(enrollment_id),
                    status=str(gate.get("stop_status") or "cancelled"),
                    next_run_at=None,
                    locked_until=None,
                    locked_by=None,
                )
            ops.resolve_approval(workspace_id, approval_id, "rejected")
            return {"ok": False, "reason": reason, "stopped": bool(gate.get("stop")), "approval": approval}

        lead_row = gate["lead"]
        campaign = gate.get("campaign")
        step = gate["step"]
        steps = gate["steps"]
        step_index = int(gate["step_index"])
        subject = str(approval.get("subject") or step.get("subject") or "")
        body = str(approval.get("draft_body") or step.get("body") or "")

        send_result = self._send_message(
            to_email=str(lead_row.get("email") or approval.get("recipient") or ""),
            subject=subject,
            body=body,
            dry_run=dry_run,
        )
        # Mark approved (and stamp sent_at when send reports success / dry)
        resolved = ops.resolve_approval(workspace_id, approval_id, "approved")
        if not send_result.get("sent") and not send_result.get("dry_run"):
            # Keep enrollment parked / retryable without advancing
            self.store.update_enrollment(
                str(enrollment_id),
                status="active",
                next_run_at=_iso(now_dt + timedelta(minutes=5)),
                last_error=str(send_result.get("error") or "send_failed"),
                locked_until=None,
                locked_by=None,
            )
            return {
                "ok": False,
                "reason": "send_failed",
                "send": send_result,
                "approval": resolved,
            }

        if send_result.get("sent") or send_result.get("dry_run"):
            if approval.get("message_id"):
                self.store._conn.execute(
                    "UPDATE outreach_messages SET sent_at = COALESCE(sent_at, ?) WHERE id = ?",
                    (now_iso, approval["message_id"]),
                )
                self.store._conn.commit()

        self._advance_enrollment_after_step(
            enrollment_id=str(enrollment_id),
            step_index=step_index,
            steps=steps,
            step=step,
            now_dt=now_dt,
            clear_attempts=True,
        )
        if lead_row.get("status") in ("new", "enrolled"):
            self.store.update_lead_status(workspace_id, str(lead_row["id"]), "contacted")
        return {
            "ok": True,
            "approval": resolved,
            "send": send_result,
            "enrollment": self.store.get_enrollment(str(enrollment_id)),
        }

    def reject_soft_wall(
        self,
        workspace_id: str,
        approval_id: str,
        *,
        stop_status: str = "cancelled",
    ) -> dict[str, Any]:
        from keprix.outreach.ops import get_outreach_ops_store

        ops = get_outreach_ops_store()
        pending = ops.list_approvals(workspace_id, status="pending")
        approval = next((r for r in pending if r.get("id") == approval_id), None)
        if not approval:
            raise LookupError("approval_not_found")
        resolved = ops.resolve_approval(workspace_id, approval_id, "rejected")
        enrollment_id = approval.get("enrollment_id")
        enrollment = None
        if enrollment_id:
            enrollment = self.store.update_enrollment(
                str(enrollment_id),
                status=stop_status,
                next_run_at=None,
                locked_until=None,
                locked_by=None,
                last_error="soft_wall_rejected",
            )
        return {"ok": True, "approval": resolved, "enrollment": enrollment}

    def get_scheduler_health(self, workspace_id: str | None = None) -> dict[str, Any]:
        return self.store.get_scheduler_health(workspace_id)

    def get_overview(self, workspace_id: str) -> dict[str, Any]:
        from keprix.outreach.ops import get_outreach_ops_store

        ops = get_outreach_ops_store()
        pipeline = self.get_pipeline(workspace_id)
        leads = self.store.list_leads(workspace_id, limit=500)
        campaigns = self.store.list_campaigns(workspace_id)
        sequences = self.store.list_sequences(workspace_id)
        active_enrollments = self.store._fetchone(
            """
            SELECT COUNT(*) AS c FROM outreach_enrollments e
            JOIN outreach_leads l ON l.id = e.lead_id
            WHERE l.workspace_id = ? AND e.status = 'active'
            """,
            (workspace_id,),
        )
        open_replies = self.store._fetchone(
            """
            SELECT COUNT(*) AS c FROM outreach_replies r
            JOIN outreach_leads l ON l.id = r.lead_id
            WHERE l.workspace_id = ? AND r.resolved = 0
            """,
            (workspace_id,),
        )
        pending_approvals = len(ops.list_approvals(workspace_id, status="pending"))
        bookings = ops.list_bookings(workspace_id)
        upcoming = [b for b in bookings if str(b.get("status") or "") in ("scheduled", "confirmed")]
        follow_up = int((pipeline.get("stages") or {}).get("follow_up") or 0)
        booked = int((pipeline.get("stages") or {}).get("booked") or 0) + int(
            (pipeline.get("stages") or {}).get("booking") or 0
        )
        default_campaign = campaigns[0] if campaigns else None
        default_sequence = sequences[0] if sequences else None
        scheduler = self.store.get_scheduler_health(workspace_id)
        return {
            "workspace_id": workspace_id,
            "summary": {
                "total_leads": len(leads),
                "active_enrollments": int((active_enrollments or {}).get("c") or 0),
                "pending_soft_wall": pending_approvals,
                "booked": booked,
                "open_reply_reviews": int((open_replies or {}).get("c") or 0),
                "upcoming_bookings": len(upcoming),
                "scheduled_reminders": 0,
                "follow_up": follow_up,
                "scheduler_queue_depth": int(scheduler.get("queue_depth") or 0),
                "scheduler_dead_letters": int(scheduler.get("dead_letter_count") or 0),
            },
            "pendingApprovals": pending_approvals,
            "activeEnrollments": int((active_enrollments or {}).get("c") or 0),
            "openReplyReviews": int((open_replies or {}).get("c") or 0),
            "upcomingBookings": len(upcoming),
            "scheduledReminders": 0,
            "scheduler": scheduler,
            "pipeline": pipeline,
            "defaults": {
                "campaign": default_campaign,
                "sequence": default_sequence,
            },
        }

    def get_pipeline_board(self, workspace_id: str) -> dict[str, Any]:
        leads = self.store.list_leads(workspace_id, limit=500)
        columns: dict[str, list[dict[str, Any]]] = {stage: [] for stage in PIPELINE_STAGES}
        for lead in leads:
            status = str(lead.get("status") or "new")
            columns.setdefault(status, [])
            columns[status].append(self._present_lead(lead))
        return {
            "workspace_id": workspace_id,
            "stages": list(PIPELINE_STAGES),
            "columns": columns,
            "summary": {k: len(v) for k, v in columns.items()},
        }

    def _present_lead(self, lead: dict[str, Any]) -> dict[str, Any]:
        first = str(lead.get("first_name") or "").strip()
        last = str(lead.get("last_name") or "").strip()
        name = f"{first} {last}".strip() or str(lead.get("email") or "Lead")
        return {
            **lead,
            "name": name,
            "tags": lead.get("tags") or [],
            "replyState": lead.get("reply_state") or "none",
            "bookingState": lead.get("booking_state") or "none",
        }

    def update_sequence(self, workspace_id: str, sequence_id: str, **fields: Any) -> dict[str, Any] | None:
        seq = self.store.get_sequence(workspace_id, sequence_id)
        if not seq:
            return None
        allowed = {
            "name",
            "channel_default",
            "stop_on_reply",
            "stop_on_booking",
            "stop_on_unsubscribe",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if updates:
            sets = []
            params: list[Any] = []
            for key, val in updates.items():
                if key.startswith("stop_on_") or key == "business_hours_only":
                    params.append(1 if val else 0)
                else:
                    params.append(val)
                sets.append(f"{key} = ?")
            params.extend([sequence_id, workspace_id])
            self.store._conn.execute(
                f"UPDATE outreach_sequences SET {', '.join(sets)} WHERE id = ? AND workspace_id = ?",
                tuple(params),
            )
            self.store._conn.commit()
        steps = fields.get("steps")
        if isinstance(steps, list) and steps:
            self.store._conn.execute(
                "DELETE FROM outreach_sequence_steps WHERE sequence_id = ?",
                (sequence_id,),
            )
            for idx, step in enumerate(steps, start=1):
                if not isinstance(step, dict):
                    continue
                self.store._conn.execute(
                    """
                    INSERT INTO outreach_sequence_steps (
                        id, sequence_id, step_order, channel, subject, body, cta, link, delay_hours
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(step.get("id") or __import__("uuid").uuid4()),
                        sequence_id,
                        int(step.get("step_order") or step.get("order") or idx),
                        step.get("channel") or "email",
                        step.get("subject"),
                        str(step.get("body") or ""),
                        step.get("cta"),
                        step.get("link"),
                        int(step.get("delay_hours") if step.get("delay_hours") is not None else 24),
                    ),
                )
            self.store._conn.commit()
        return self.store.get_sequence(workspace_id, sequence_id)

    def list_replies(self, workspace_id: str, *, resolved: bool | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT r.* FROM outreach_replies r
            JOIN outreach_leads l ON l.id = r.lead_id
            WHERE l.workspace_id = ?
        """
        params: list[Any] = [workspace_id]
        if resolved is not None:
            sql += " AND r.resolved = ?"
            params.append(1 if resolved else 0)
        sql += " ORDER BY r.created_at DESC LIMIT 200"
        return self.store._fetchall(sql, tuple(params))

    def resolve_reply(
        self,
        workspace_id: str,
        reply_id: str,
        *,
        classification: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any] | None:
        row = self.store._fetchone(
            """
            SELECT r.* FROM outreach_replies r
            JOIN outreach_leads l ON l.id = r.lead_id
            WHERE r.id = ? AND l.workspace_id = ?
            """,
            (reply_id, workspace_id),
        )
        if not row:
            return None
        self.store._conn.execute(
            """
            UPDATE outreach_replies
            SET resolved = 1, classification = COALESCE(?, classification)
            WHERE id = ?
            """,
            (classification, reply_id),
        )
        self.store._conn.commit()
        if note:
            pass
        return self.store._fetchone("SELECT * FROM outreach_replies WHERE id = ?", (reply_id,))

    def import_companies_house_lead(self, workspace_id: str, body: dict[str, Any]) -> dict[str, Any]:
        company_name = str(body.get("company_name") or "").strip()
        company_number = str(body.get("company_number") or "").strip()
        email = str(body.get("email") or "").strip()
        if not email:
            # Placeholder for operator to fill; still create lead with synthetic email
            slug = (company_number or company_name or "company").lower().replace(" ", "")[:40]
            email = f"{slug}@companies-house.invalid"
        parts = company_name.split(None, 1)
        tags = list(body.get("tags") or [])
        if company_number:
            tags.append(f"ch:{company_number}")
        result = self.add_leads(
            workspace_id,
            leads=[
                {
                    "email": email,
                    "first_name": parts[0] if parts else company_name,
                    "last_name": parts[1] if len(parts) > 1 else "",
                    "company": company_name,
                    "source": "companies_house",
                    "tags": tags,
                    "notes": json_dumps_safe(
                        {
                            "company_number": company_number,
                            "company_status": body.get("company_status"),
                            "registered_office": body.get("registered_office"),
                            "sic_codes": body.get("sic_codes"),
                            "officer_names": body.get("officer_names"),
                        }
                    ),
                }
            ],
        )
        lead = (result.get("leads") or [None])[0]
        return {"lead": self._present_lead(lead) if lead else None, "created": bool(lead)}

    def parse_pipe_leads(self, text: str) -> list[dict[str, Any]]:
        leads: list[dict[str, Any]] = []
        for line in (text or "").splitlines():
            line = line.strip()
            if not line or line.lower().startswith("name"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                continue
            name, email = parts[0], parts[1]
            company = parts[2] if len(parts) > 2 else ""
            phone = parts[3] if len(parts) > 3 else ""
            name_parts = name.split(None, 1)
            leads.append(
                {
                    "email": email,
                    "first_name": name_parts[0] if name_parts else name,
                    "last_name": name_parts[1] if len(name_parts) > 1 else "",
                    "company": company or None,
                    "phone": phone or None,
                    "source": "pipe_import",
                }
            )
        return leads

    def classify_and_apply_reply(
        self,
        workspace_id: str,
        *,
        from_address: str,
        body: str,
        subject: str = "",
        lead_id: str | None = None,
        message_id: str | None = None,
        classification: str | None = None,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        lead = None
        if lead_id:
            lead = self.store.get_lead(workspace_id, lead_id)
        if not lead:
            lead = self.store.find_lead_by_email(workspace_id, from_address)
        if not lead:
            raise LookupError("lead_not_found")

        if classification:
            result = {
                "classification": classification,
                "confidence": float(confidence if confidence is not None else 1.0),
                "method": "provided",
            }
        else:
            result = classify_reply_sync(subject, body, from_address)

        label = str(result["classification"])
        reply = self.store.create_reply(
            lead_id=lead["id"],
            message_id=message_id,
            from_address=from_address,
            subject=subject,
            body=body,
            classification=label,
            confidence=result.get("confidence"),
        )

        new_status = lead_status_for_classification(label)
        self.store.update_lead_status(workspace_id, str(lead["id"]), new_status)

        stopped: list[str] = []
        for enrollment in self.store.active_enrollments_for_lead(str(lead["id"])):
            seq = self.store.get_sequence(workspace_id, str(enrollment["sequence_id"])) or {}
            stop = enrollment_stop_status(label, seq)
            if stop:
                self.store.update_enrollment(enrollment["id"], status=stop, next_run_at=None)
                stopped.append(str(enrollment["id"]))

        draft = None
        if label == "objection":
            draft = (
                f"Thanks for the candid feedback. Happy to address the concern around "
                f"your note. Would a short call help? {subject or ''}".strip()
            )
        elif label == "booking_intent":
            campaign = (
                self.store.get_campaign(workspace_id, str(lead["campaign_id"]))
                if lead.get("campaign_id")
                else None
            )
            link = (campaign or {}).get("default_booking_link") or "{{booking_link}}"
            draft = f"Great — please pick a time here: {link}"

        try:
            from keprix.aiva_analytics.metrics import record_outreach_reply

            record_outreach_reply(workspace_id, classification=label)
        except Exception:
            pass

        out = {
            "reply": reply,
            "classification": result,
            "lead": self.store.get_lead(workspace_id, str(lead["id"])),
            "stopped_enrollments": stopped,
            "draft_response": draft,
        }
        try:
            from keprix.crm.engagement import hook_soft_wall_reply

            out["crm"] = hook_soft_wall_reply(workspace_id, out)
        except Exception as exc:
            out["crm_error"] = str(exc)
        return out

    def scan_replies(self, workspace_id: str | None = None) -> dict[str, Any]:
        """Scan inbox for replies when email poller data is available; otherwise no-op."""
        return {
            "scanned": 0,
            "matched": 0,
            "workspace_id": workspace_id,
            "note": "inbox_scan_requires_email_account; use outreach_classify_reply for inbound payloads",
        }

    def daily_digest(self, workspace_id: str, *, hours: int = 24) -> dict[str, Any]:
        since = _iso(_utcnow() - timedelta(hours=hours))
        summary = self.store.digest_summary(workspace_id, since)
        summary["message"] = (
            f"Outreach digest for {workspace_id}: "
            f"{summary['new_leads']} new leads, {summary['replies']} replies, "
            f"{summary['bookings']} bookings (last {hours}h)."
        )
        return summary


def json_dumps_safe(value: Any) -> str:
    import json

    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def get_outreach_service(store: OutreachStore | None = None) -> OutreachService:
    return OutreachService(store=store)
