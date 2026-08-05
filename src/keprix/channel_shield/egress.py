"""Real channel egress helpers (SMTP / Slack / Telegram / Discord / WhatsApp / SMS / web)."""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


async def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    form: dict[str, str] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    try:
        import httpx
    except ImportError:
        return {"ok": False, "error": "httpx not installed", "mode": "unavailable"}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if form is not None:
                resp = await client.request(method, url, headers=headers, data=form)
            else:
                resp = await client.request(method, url, headers=headers, json=json_body)
            body: Any
            try:
                body = resp.json()
            except Exception:
                body = {"text": resp.text[:500]}
            return {
                "ok": 200 <= resp.status_code < 300,
                "status_code": resp.status_code,
                "body": body,
            }
    except Exception as exc:
        logger.warning("Channel Shield egress HTTP failed: %s", exc)
        return {"ok": False, "error": str(exc)}


async def deliver_email_smtp(
    *,
    to_addrs: list[str],
    subject: str,
    body: str,
    from_addr: str | None = None,
    user_id: str = "local",
) -> dict[str, Any]:
    """Send via first active email account SMTP, or report missing config."""
    if not to_addrs:
        return {"ok": False, "mode": "smtp", "error": "no recipients"}
    try:
        from keprix.email.helpers import send_smtp_message
        from keprix.email.store import get_email_store

        accounts = await get_email_store().list_accounts(user_id)
        if not accounts:
            accounts = await get_email_store().list_active_accounts()
        if not accounts:
            return {
                "ok": False,
                "mode": "smtp",
                "queued": True,
                "error": "no email account configured for SMTP deliver",
            }
        account = accounts[0]
        account_dict = account.to_dict() if hasattr(account, "to_dict") else dict(account)
        sender = from_addr or account_dict.get("email") or account_dict.get("username") or ""
        await __import__("asyncio").to_thread(
            send_smtp_message,
            account_dict,
            from_addr=sender,
            to_addresses=list(to_addrs),
            cc_addresses=[],
            subject=subject,
            body=body,
        )
        return {"ok": True, "mode": "smtp", "to": list(to_addrs), "from": sender}
    except Exception as exc:
        logger.warning("Channel Shield email SMTP deliver failed: %s", exc)
        return {"ok": False, "mode": "smtp", "error": str(exc)}


async def slack_post_message(
    *,
    channel: str,
    text: str,
    thread_ts: str | None = None,
) -> dict[str, Any]:
    token = (os.environ.get("SLACK_BOT_TOKEN") or "").strip()
    if not token or not channel:
        return {
            "ok": False,
            "mode": "slack_api",
            "queued": True,
            "error": "SLACK_BOT_TOKEN or channel missing",
        }
    payload: dict[str, Any] = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    result = await http_json(
        "POST",
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json_body=payload,
    )
    result["mode"] = "slack_api"
    return result


async def telegram_send_message(*, chat_id: str, text: str) -> dict[str, Any]:
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token or not chat_id:
        return {
            "ok": False,
            "mode": "telegram_api",
            "queued": True,
            "error": "TELEGRAM_BOT_TOKEN or chat_id missing",
        }
    # Telegram hard limit ~4096; safe summaries truncate upstream
    result = await http_json(
        "POST",
        f"https://api.telegram.org/bot{token}/sendMessage",
        json_body={"chat_id": chat_id, "text": text[:4000]},
    )
    result["mode"] = "telegram_api"
    return result


async def discord_send_message(
    *,
    channel_id: str,
    text: str,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    if webhook_url:
        result = await http_json("POST", webhook_url, json_body={"content": text[:1900]})
        result["mode"] = "discord_webhook"
        return result
    token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    if not token or not channel_id:
        return {
            "ok": False,
            "mode": "discord_api",
            "queued": True,
            "error": "DISCORD_BOT_TOKEN/webhook or channel_id missing",
        }
    result = await http_json(
        "POST",
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
        json_body={"content": text[:1900]},
    )
    result["mode"] = "discord_api"
    return result


async def whatsapp_send_text(*, to: str, text: str, phone_number_id: str | None = None) -> dict[str, Any]:
    token = (os.environ.get("WHATSAPP_TOKEN") or os.environ.get("WHATSAPP_CLOUD_TOKEN") or "").strip()
    phone_id = (
        phone_number_id
        or (os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
    )
    if not token or not phone_id or not to:
        return {
            "ok": False,
            "mode": "whatsapp_cloud",
            "queued": True,
            "error": "WhatsApp token/phone_number_id/to missing",
        }
    result = await http_json(
        "POST",
        f"https://graph.facebook.com/v19.0/{phone_id}/messages",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json_body={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text[:4000]},
        },
    )
    result["mode"] = "whatsapp_cloud"
    return result


async def sms_send_twilio(*, to: str, body: str, from_number: str | None = None) -> dict[str, Any]:
    sid = (os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
    token = (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    frm = from_number or (os.environ.get("TWILIO_FROM_NUMBER") or "").strip()
    if not sid or not token or not frm or not to:
        return {
            "ok": False,
            "mode": "twilio",
            "queued": True,
            "error": "Twilio credentials or numbers missing",
        }
    import base64

    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    result = await http_json(
        "POST",
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        headers={"Authorization": f"Basic {auth}"},
        form={"To": to, "From": frm, "Body": body[:1500]},
    )
    result["mode"] = "twilio"
    return result


async def teams_send_activity(
    *,
    service_url: str,
    conversation_id: str,
    text: str,
    access_token: str | None = None,
) -> dict[str, Any]:
    token = (access_token or os.environ.get("TEAMS_BOT_TOKEN") or "").strip()
    if not token or not service_url or not conversation_id:
        return {
            "ok": False,
            "mode": "teams_bot",
            "queued": True,
            "error": "Teams token/service_url/conversation missing",
        }
    url = service_url.rstrip("/") + f"/v3/conversations/{conversation_id}/activities"
    result = await http_json(
        "POST",
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json_body={"type": "message", "text": text[:4000]},
    )
    result["mode"] = "teams_bot"
    return result


async def web_callback(*, callback_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not callback_url:
        return {
            "ok": False,
            "mode": "web_callback",
            "queued": True,
            "error": "callback_url missing",
        }
    result = await http_json("POST", callback_url, json_body=payload)
    result["mode"] = "web_callback"
    return result


def deep_link_query(message_id: str) -> str:
    return urlencode({"message": message_id})
