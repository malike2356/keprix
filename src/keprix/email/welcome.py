"""Welcome email and chat-first ABC onboarding handoff."""

from __future__ import annotations

import html
import os
from typing import Any

from keprix.notify_external.smtp_sender import send_email


def welcome_email_enabled() -> bool:
    value = os.environ.get("KEPRIX_WELCOME_EMAIL_ENABLED", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _instance_url() -> str:
    return os.environ.get("KEPRIX_INSTANCE_URL", "http://localhost:3000").rstrip("/")


def welcome_content(*, recipient_name: str, workspace_name: str) -> dict[str, str]:
    name = recipient_name.strip() or "there"
    workspace = workspace_name.strip() or "your workspace"
    chat_url = f"{_instance_url()}/chat-only"
    safe_name = html.escape(name)
    safe_workspace = html.escape(workspace)
    return {
        "subject": f"Welcome to Keprix, {name}",
        "text": (
            f"Hi {name},\n\n"
            f"Your Keprix workspace, {workspace}, is ready. Start with one useful question, "
            "then build one artifact and connect a channel when you are ready.\n\n"
            f"Start chatting: {chat_url}\n\n"
            "Ask, Build, Connect. You can skip any step and return later."
        ),
        "html": (
            f"<p>Hi {safe_name},</p>"
            f"<p>Your Keprix workspace, <strong>{safe_workspace}</strong>, is ready. "
            "Start with one useful question, then build one artifact and connect "
            "a channel when you are ready.</p>"
            f'<p><a href="{html.escape(chat_url, quote=True)}">Start chatting</a></p>'
            "<p><strong>Ask, Build, Connect.</strong> You can skip any step and return later.</p>"
        ),
    }


async def send_welcome_email(
    *,
    workspace_id: str,
    workspace_name: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    email = str(user.get("email") or "").strip()
    if not email:
        return {"status": "skipped", "reason": "no_email"}
    if not welcome_email_enabled():
        return {"status": "skipped", "reason": "sending_disabled"}
    content = welcome_content(
        recipient_name=str(user.get("username") or user.get("name") or "there"),
        workspace_name=workspace_name,
    )
    confirmation = await send_email(
        workspace_id,
        email,
        subject=content["subject"],
        body_text=content["text"],
        body_html=content["html"],
        triggered_by="workspace_welcome",
        triggered_by_id=workspace_id,
    )
    return {"status": "sent", "provider_confirmation_id": confirmation}
