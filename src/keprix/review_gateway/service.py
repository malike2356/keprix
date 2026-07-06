"""Review gateway business logic."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.review_gateway.dispatch import (
    dispatch_cancellation,
    dispatch_decision_receipt,
    dispatch_review_notification,
)
from keprix.review_gateway.store import ReviewRequest, get_review_store
from keprix.review_gateway.tokens import generate_review_token, validate_review_token


def _parse_expires(expires_at: str) -> datetime:
    dt = datetime.fromisoformat(expires_at)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def create_review_request(
    *,
    workspace_id: str,
    title: str,
    context_message: str,
    artifact_type: str,
    artifact_content: str = "",
    artifact_url: str = "",
    artifact_filename: str = "",
    reviewer_name: str,
    reviewer_email: str,
    reviewer_webhook_url: str = "",
    allowed_actions: list[str] | None = None,
    expires_in_hours: int = 48,
    reminder_in_hours: int | None = None,
    playbook_run_id: str | None = None,
    playbook_step_id: str | None = None,
    domain_pack: str = "",
    created_by_user_id: str | None = None,
    base_url: str = "http://localhost:8000",
) -> tuple[ReviewRequest, str]:
    store = get_review_store()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    reminder_at = None
    if reminder_in_hours is not None:
        reminder_at = (datetime.now(timezone.utc) + timedelta(hours=reminder_in_hours)).isoformat()
    token_id, url_token = generate_review_token(
        review_request_id="pending",
        workspace_id=workspace_id,
        expires_at=expires_at,
    )
    req = store.create(
        workspace_id=workspace_id,
        title=title,
        context_message=context_message,
        artifact_type=artifact_type,
        artifact_content=artifact_content,
        artifact_url=artifact_url,
        artifact_filename=artifact_filename,
        reviewer_name=reviewer_name,
        reviewer_email=reviewer_email,
        reviewer_webhook_url=reviewer_webhook_url,
        allowed_actions=allowed_actions or ["approve", "reject"],
        token_id=token_id,
        expires_at=expires_at.isoformat(),
        reminder_at=reminder_at,
        playbook_run_id=playbook_run_id,
        playbook_step_id=playbook_step_id,
        domain_pack=domain_pack,
        created_by_user_id=created_by_user_id,
    )
    token_id, url_token = generate_review_token(
        review_request_id=req.id,
        workspace_id=workspace_id,
        expires_at=expires_at,
    )
    req.token_id = token_id
    store.update(req)
    review_url = f"{base_url.rstrip('/')}/review/{url_token}"
    await dispatch_review_notification(req, review_url=review_url)
    return req, url_token


async def submit_review_decision(
    *,
    url_token: str,
    action: str,
    reviewer_note: str,
    reviewer_ip_hash: str,
) -> ReviewRequest:
    from fastapi import HTTPException

    store = get_review_store()
    decoded = url_token
    from keprix.review_gateway.tokens import decode_url_token

    parsed = decode_url_token(url_token)
    if parsed is None:
        raise HTTPException(status_code=404, detail="Invalid review token")
    token_id, _ = parsed
    req = store.get_by_token_id(token_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Invalid review token")
    if req.status == "decided":
        raise HTTPException(status_code=410, detail="Review already completed")
    if req.status in {"expired", "cancelled"}:
        raise HTTPException(status_code=410, detail="Review no longer valid")
    expires = _parse_expires(req.expires_at)
    if not validate_review_token(
        decoded,
        token_id=req.token_id,
        review_request_id=req.id,
        workspace_id=req.workspace_id,
        expires_at=expires,
        status=req.status,
    ):
        raise HTTPException(status_code=404, detail="Invalid review token")
    if action not in req.allowed_actions:
        raise HTTPException(status_code=400, detail="Action not allowed")
    store.record_decision(req, action=action, reviewer_note=reviewer_note, reviewer_ip_hash=reviewer_ip_hash)
    await dispatch_decision_receipt(req, action, reviewer_note)
    await resume_playbook_after_review(req, action=action, reviewer_note=reviewer_note)
    return req


async def cancel_review_request(request_id: str, workspace_id: str) -> ReviewRequest:
    from fastapi import HTTPException

    store = get_review_store()
    req = store.get(request_id)
    if req is None or req.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Review request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be cancelled")
    req.status = "cancelled"
    store.update(req)
    await dispatch_cancellation(req)
    return req


async def resume_playbook_after_review(
    req: ReviewRequest,
    *,
    action: str,
    reviewer_note: str = "",
) -> None:
    if not req.playbook_run_id:
        return
    from keprix.playbook.runtime import playbook_registry

    try:
        await playbook_registry.resume(
            req.playbook_run_id,
            state_patch={
                "review_action": action,
                "reviewer_note": reviewer_note,
                "review_request_id": req.id,
            },
            approved_by=req.reviewer_name,
        )
    except Exception:
        return


def lookup_request_by_token(url_token: str) -> ReviewRequest | None:
    from keprix.review_gateway.tokens import decode_url_token

    parsed = decode_url_token(url_token)
    if parsed is None:
        return None
    token_id, _ = parsed
    return get_review_store().get_by_token_id(token_id)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(16)
