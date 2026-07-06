"""Slack slash command adapter."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

from keprix.slash.executor import build_context, execute_context
from keprix.slash.renderers import render_slack


def verify_slack_signature(
    *,
    signing_secret: str,
    timestamp: str,
    body: bytes,
    signature: str,
    max_age_seconds: int = 300,
) -> bool:
    if not signing_secret or not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > max_age_seconds:
        return False
    base = f"v0:{timestamp}:{body.decode('utf-8')}"
    digest = hmac.new(signing_secret.encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, signature)


async def handle_slack_slash(
    *,
    text: str,
    user_id: str,
    workspace_id: str,
    channel_id: str,
    role: str | None = None,
) -> dict[str, Any]:
    normalized = text if text.startswith("/") else f"/{text.lstrip('/')}"
    if normalized.startswith("/carina "):
        normalized = "/" + normalized[len("/carina ") :]
    ctx = build_context(
        raw_text=normalized,
        user_id=user_id,
        workspace_id=workspace_id,
        channel="slack",
        channel_user_id=channel_id,
        role=role,
    )
    result = await execute_context(ctx)
    return render_slack(result)
