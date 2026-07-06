"""Channel-specific slash response renderers."""

from __future__ import annotations

from typing import Any

from keprix.slash.schemas import SlashResult


def render_text(result: SlashResult) -> str:
    return result.message


def render_telegram(result: SlashResult) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": result.message, "parse_mode": "Markdown"}
    if result.requires_confirmation and result.confirmation_token:
        payload["reply_markup"] = telegram_confirm_keyboard(result.confirmation_token)
    return payload


def telegram_confirm_keyboard(token: str) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "Approve", "callback_data": f"slash:approve:{token}"},
                {"text": "Cancel", "callback_data": f"slash:cancel:{token}"},
            ]
        ]
    }


def render_discord(result: SlashResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "content": result.message,
        "ephemeral": result.ephemeral or result.requires_confirmation,
    }
    if result.requires_confirmation and result.confirmation_token:
        payload["components"] = [
            {
                "type": 1,
                "components": [
                    {"type": 2, "style": 3, "label": "Approve", "custom_id": f"slash:approve:{result.confirmation_token}"},
                    {"type": 2, "style": 4, "label": "Cancel", "custom_id": f"slash:cancel:{result.confirmation_token}"},
                ],
            }
        ]
    return payload


def render_slack(result: SlashResult) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = [{"type": "section", "text": {"type": "mrkdwn", "text": result.message}}]
    if result.requires_confirmation and result.confirmation_token:
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "action_id": "slash_approve",
                        "value": result.confirmation_token,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Cancel"},
                        "action_id": "slash_cancel",
                        "value": result.confirmation_token,
                    },
                ],
            }
        )
    return {"response_type": "ephemeral" if result.ephemeral or result.requires_confirmation else "in_channel", "blocks": blocks}


def render_webchat(result: SlashResult) -> dict[str, Any]:
    return {
        "message": result.message,
        "ephemeral": result.ephemeral,
        "requires_confirmation": result.requires_confirmation,
        "confirmation_token": result.confirmation_token,
        "blocks": result.blocks,
    }
