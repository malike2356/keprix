"""Approver notifications for pending pack gate records."""

from __future__ import annotations

from typing import Any

from keprix.backend.notifications.inbox import get_inbox_service


async def notify_pack_pending_approval(
    *,
    workspace_id: str,
    pack_name: str,
    to_version: str,
    approver_email: str | None,
    gate_record_id: str,
    sign_off_url: str,
) -> dict[str, Any]:
    message = (
        f"A new version of '{pack_name}' (v{to_version}) is awaiting your approval to activate."
    )
    metadata = {
        "pack_name": pack_name,
        "to_version": to_version,
        "gate_record_id": gate_record_id,
        "sign_off_url": sign_off_url,
    }
    if approver_email:
        metadata["email_recipient"] = approver_email

    notification = await get_inbox_service().send_notification(
        workspace_id,
        "pack_gate_pending",
        severity="warning",
        title=f"Pack approval needed: {pack_name}",
        message=message,
        href=sign_off_url,
        sensitive=False,
        metadata=metadata,
        source="pack_gate",
        source_id=gate_record_id,
    )

    email_result: dict[str, Any] = {"queued": False}
    if approver_email:
        try:
            from keprix.notify_external.smtp_sender import send_email

            notification_id = await send_email(
                workspace_id,
                approver_email,
                template_name="pack_gate_pending",
                template_vars={
                    "pack_name": pack_name,
                    "version": to_version,
                    "message": message,
                    "sign_off_url": sign_off_url,
                },
                triggered_by="pack_gate",
                triggered_by_id=gate_record_id,
            )
            email_result = {"queued": True, "notification_id": notification_id}
        except Exception:
            email_result = {"queued": False, "to": approver_email, "fallback": True}

    return {"inbox": True, "notification_id": notification.get("id"), "email": email_result}
