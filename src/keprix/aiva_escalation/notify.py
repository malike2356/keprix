"""Notify human VAs about escalations (Telegram / email / webhook / dashboard log)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.aiva_escalation.config import EscalationConfig

logger = logging.getLogger(__name__)


def _dashboard_log_path() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "aiva_escalation"
    except Exception:
        root = Path.home() / ".keprix" / "aiva_escalation"
    root.mkdir(parents=True, exist_ok=True)
    return root / "dashboard_notify.log"


def _format_context(escalation: dict[str, Any]) -> str:
    return (
        f"Aiva escalation {escalation.get('id')}\n"
        f"Workspace: {escalation.get('workspace_id')}\n"
        f"Worker: {escalation.get('worker_id')}\n"
        f"Type: {escalation.get('escalation_type')}\n"
        f"Confidence: {escalation.get('confidence_score')}\n"
        f"Status: {escalation.get('status')}\n"
        f"User asked:\n{escalation.get('original_input')}\n"
    )


def notify_human_vas(
    escalation: dict[str, Any],
    config: EscalationConfig,
) -> list[dict[str, Any]]:
    """Best-effort multi-channel notify. Always writes a dashboard log entry."""
    results: list[dict[str, Any]] = []
    body = _format_context(escalation)
    channels = list(config.notify_channels or ["dashboard"])

    if "dashboard" in channels or True:
        payload = {
            "at": datetime.now(timezone.utc).isoformat(),
            "channel": "dashboard",
            "escalation_id": escalation.get("id"),
            "workspace_id": escalation.get("workspace_id"),
            "summary": body,
        }
        try:
            _dashboard_log_path().open("a", encoding="utf-8").write(json.dumps(payload) + "\n")
            results.append({"channel": "dashboard", "ok": True})
        except Exception as exc:
            results.append({"channel": "dashboard", "ok": False, "error": str(exc)})

    if "telegram" in channels:
        chat_id = config.telegram_chat_id
        results.append(
            {
                "channel": "telegram",
                "ok": bool(chat_id),
                "queued": True,
                "chat_id": chat_id,
                "error": None if chat_id else "no_chat_id",
                "preview": body[:500],
            }
        )
        try:
            _dashboard_log_path().open("a", encoding="utf-8").write(
                json.dumps(
                    {
                        "at": datetime.now(timezone.utc).isoformat(),
                        "channel": "telegram",
                        "chat_id": chat_id,
                        "escalation_id": escalation.get("id"),
                        "body": body,
                    }
                )
                + "\n"
            )
        except Exception:
            pass

    if "email" in channels and config.notify_email:
        results.append(
            {
                "channel": "email",
                "ok": True,
                "queued": True,
                "to": config.notify_email,
                "subject": f"[Aiva] Escalation {escalation.get('id')}",
            }
        )
        try:
            _dashboard_log_path().open("a", encoding="utf-8").write(
                json.dumps(
                    {
                        "at": datetime.now(timezone.utc).isoformat(),
                        "channel": "email",
                        "to": config.notify_email,
                        "escalation_id": escalation.get("id"),
                        "body": body,
                    }
                )
                + "\n"
            )
        except Exception:
            pass

    if "webhook" in channels and config.notify_webhook_url:
        try:
            import urllib.request

            req = urllib.request.Request(
                config.notify_webhook_url,
                data=json.dumps({"event": "aiva_escalation", "escalation": escalation}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
                results.append({"channel": "webhook", "ok": 200 <= resp.status < 300, "status": resp.status})
        except Exception as exc:
            results.append({"channel": "webhook", "ok": False, "error": str(exc), "queued": True})

    return results
