"""External notification HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.notify_external.smtp_sender import RateLimitExceeded, SMTPNotConfigured, send_email
from keprix.notify_external.store import get_notify_external_store, recipient_domain
from keprix.notify_external.templates import TEMPLATES, list_template_names, sanitize_template_html
from keprix.notify_external.webhook_sender import WebhookTargetRejected, send_webhook

router = APIRouter(prefix="/api/notify-external", tags=["notify-external"])


def _workspace_id(request: Request) -> str:
    return request.headers.get("x-workspace-id", "default").strip() or "default"


class SendBody(BaseModel):
    channel: str
    recipient_address: str
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    template_name: str | None = None
    template_vars: dict[str, Any] | None = None
    triggered_by: str | None = "api"
    triggered_by_id: str | None = None
    webhook_payload: dict[str, Any] | None = None


class ConfigBody(BaseModel):
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str | None = None
    max_retries: int = 3
    retry_interval_seconds: int = 300


class TestEmailBody(BaseModel):
    to_email: str


class TemplateBody(BaseModel):
    name: str = Field(..., min_length=1)
    subject_template: str
    text_template: str
    html_template: str | None = None


def _public_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        **config,
        "smtp_password_vault_id": "configured" if config.get("smtp_password_vault_id") else "not set",
        "webhook_signing_secret_vault_id": (
            "configured" if config.get("webhook_signing_secret_vault_id") else "not set"
        ),
    }


def _public_notification(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "workspace_id": row.get("workspace_id"),
        "channel": row.get("channel"),
        "recipient_domain": recipient_domain(str(row.get("recipient_address") or "")),
        "subject": row.get("subject"),
        "template_name": row.get("template_name"),
        "status": row.get("status"),
        "attempts": row.get("attempts"),
        "last_attempted_at": row.get("last_attempted_at"),
        "delivered_at": row.get("delivered_at"),
        "failure_reason": row.get("failure_reason"),
        "triggered_by": row.get("triggered_by"),
        "triggered_by_id": row.get("triggered_by_id"),
        "created_at": row.get("created_at"),
    }


@router.post("/send")
async def send_notification(body: SendBody, request: Request, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    try:
        if body.channel == "email":
            notification_id = await send_email(
                workspace_id,
                body.recipient_address,
                subject=body.subject,
                body_text=body.body_text,
                body_html=body.body_html,
                template_name=body.template_name,
                template_vars=body.template_vars,
                triggered_by=body.triggered_by or "api",
                triggered_by_id=body.triggered_by_id,
            )
            row = get_notify_external_store().get_notification(notification_id)
            return {"notification_id": notification_id, "status": row.get("status") if row else "pending"}
        if body.channel == "webhook":
            payload = body.webhook_payload or body.template_vars or {}
            notification_id = await send_webhook(
                workspace_id,
                body.recipient_address,
                payload,
                triggered_by=body.triggered_by or "api",
                triggered_by_id=body.triggered_by_id,
            )
            row = get_notify_external_store().get_notification(notification_id)
            return {"notification_id": notification_id, "status": row.get("status") if row else "pending"}
        raise HTTPException(status_code=422, detail="channel must be email or webhook")
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "3600"}) from exc
    except WebhookTargetRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SMTPNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/notifications")
async def list_notifications(
    request: Request,
    status: str | None = None,
    channel: str | None = None,
    triggered_by: str | None = None,
    page: int = 1,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    limit = 50
    offset = max(page - 1, 0) * limit
    rows, total = get_notify_external_store().list_notifications(
        workspace_id,
        status=status,
        channel=channel,
        triggered_by=triggered_by,
        limit=limit,
        offset=offset,
    )
    return {"notifications": [_public_notification(row) for row in rows], "total": total}


@router.get("/notifications/{notification_id}")
async def get_notification(notification_id: str, request: Request, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    row = get_notify_external_store().get_notification(notification_id)
    if row is None or row.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    return _public_notification(row)


@router.get("/config")
async def get_config(request: Request, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return _public_config(get_notify_external_store().get_config(_workspace_id(request)))


@router.put("/config")
async def put_config(body: ConfigBody, request: Request, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    patch: dict[str, Any] = body.model_dump(exclude_none=True)
    password = patch.pop("smtp_password", None)
    if password:
        from keprix.security.vault_service import get_vault_service

        item = await get_vault_service().create_item(
            user_id="system",
            label=f"notify-external-smtp-{workspace_id}",
            category="smtp",
            value=password,
        )
        patch["smtp_password_vault_id"] = item.id
    config = get_notify_external_store().save_config(workspace_id, patch)
    return _public_config(config)


@router.post("/test-email")
async def test_email(body: TestEmailBody, request: Request, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    try:
        notification_id = await send_email(
            workspace_id,
            body.to_email,
            subject="Keprix external notification test",
            body_text="This is a test email from your Keprix workspace SMTP configuration.",
            triggered_by="manual",
        )
        row = get_notify_external_store().get_notification(notification_id)
        return {"notification_id": notification_id, "status": row.get("status") if row else "pending"}
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "3600"}) from exc
    except SMTPNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/templates")
async def list_templates(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    builtin = []
    for name in list_template_names():
        template = TEMPLATES[name]
        vars_found = {part.strip("}") for part in template["subject"].split("{") if "}" in part}
        for key in template["text"].split("{"):
            if "}" in key:
                vars_found.add(key.split("}", 1)[0])
        builtin.append({"name": name, "variables": sorted(vars_found)})
    custom = get_notify_external_store().list_custom_templates()
    return {"templates": builtin + [{"name": row["name"], "variables": [], "custom": True} for row in custom]}


@router.post("/templates")
async def create_template(body: TemplateBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    html = body.html_template or ""
    if html:
        sanitize_template_html(html)
    template = {
        "name": body.name,
        "subject": body.subject_template,
        "text": body.text_template,
        "html": html,
    }
    get_notify_external_store().save_custom_template(template)
    TEMPLATES[body.name] = {
        "subject": body.subject_template,
        "text": body.text_template,
        "html": html,
    }
    return {"template": {"name": body.name}}
