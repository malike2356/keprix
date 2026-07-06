"""Setup validation probes."""

from __future__ import annotations

from typing import Any


async def validate_service(service_id: str, fields: dict[str, str]) -> dict[str, Any]:
    if service_id == "openai":
        key = fields.get("api_key", "")
        if not key.startswith("sk-"):
            return {"ok": False, "summary": "OpenAI keys usually start with sk-"}
        return {"ok": True, "summary": "OpenAI key format accepted"}
    if service_id == "anthropic":
        key = fields.get("api_key", "")
        if len(key) < 20:
            return {"ok": False, "summary": "Anthropic API key too short"}
        return {"ok": True, "summary": "Anthropic key format accepted"}
    if service_id == "telegram":
        token = fields.get("bot_token", "")
        if ":" not in token:
            return {"ok": False, "summary": "Telegram bot token must contain a colon"}
        return {"ok": True, "summary": "Telegram token format accepted"}
    if service_id == "email":
        if not fields.get("imap_host") or not fields.get("smtp_host"):
            return {"ok": False, "summary": "IMAP and SMTP hosts are required"}
        return {"ok": True, "summary": "Email credentials accepted for storage"}
    return {"ok": False, "summary": f"Unknown service {service_id}"}
