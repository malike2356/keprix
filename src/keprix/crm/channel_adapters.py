"""Thin Slack / WhatsApp adapters for channel journey (Prompt 627).

Telegram initiation is REAL via ``telegram_funnel``. Slack and WhatsApp call the
same ``run_channel_journey`` when channel hooks exist; otherwise they return
PARTIAL status so operators do not confuse UI presence with full parity.
"""

from __future__ import annotations

from typing import Any


def slack_channel_journey(
    workspace_id: str,
    *,
    payload: bytes | None = None,
    filename: str | None = None,
    actor_id: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Slack adapter: same durable journey when attachment bytes are present."""
    if payload is None:
        return {
            "ok": False,
            "partial": True,
            "channel": "slack",
            "classification": "PARTIAL",
            "note": (
                "Slack journey adapter is thin. Provide spreadsheet attachment bytes "
                "to run the shared channel_journey; otherwise Telegram remains the "
                "primary REAL channel initiation path."
            ),
        }
    from keprix.crm.channel_journey import run_channel_journey

    result = run_channel_journey(
        workspace_id,
        payload=payload,
        filename=filename or "slack-upload.csv",
        channel="slack",
        actor_id=actor_id,
        **kwargs,
    )
    result["channel_adapter"] = "slack"
    return result


def whatsapp_channel_journey(
    workspace_id: str,
    *,
    payload: bytes | None = None,
    filename: str | None = None,
    actor_id: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """WhatsApp adapter: same durable journey when attachment bytes are present."""
    if payload is None:
        return {
            "ok": False,
            "partial": True,
            "channel": "whatsapp",
            "classification": "PARTIAL",
            "note": (
                "WhatsApp journey adapter is thin. Provide spreadsheet attachment "
                "bytes to run the shared channel_journey; Telegram remains REAL for "
                "operator funnel intents."
            ),
        }
    from keprix.crm.channel_journey import run_channel_journey

    result = run_channel_journey(
        workspace_id,
        payload=payload,
        filename=filename or "whatsapp-upload.csv",
        channel="whatsapp",
        actor_id=actor_id,
        **kwargs,
    )
    result["channel_adapter"] = "whatsapp"
    return result


def channel_journey_parity() -> dict[str, Any]:
    return {
        "telegram": "REAL",
        "slack": "PARTIAL",
        "whatsapp": "PARTIAL",
        "email_ingest": "REAL_DEFAULT_OFF",
        "shared_pipeline": "keprix.crm.channel_journey.run_channel_journey",
    }
