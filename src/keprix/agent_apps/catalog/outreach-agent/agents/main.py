"""Outreach Lead Agent entrypoint."""
from __future__ import annotations
from typing import Any
from keprix.agent_os.workflows.outreach_agent import generate_outreach_package

def run(input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    form = (context or {}).get("form") or {}
    audience = str(form.get("audience") or input_text or "").strip()
    offer = str(form.get("offer") or "a working demo").strip()
    channels = [c.strip() for c in str(form.get("channels") or "linkedin,email,x").split(",") if c.strip()]
    try:
        days = int(str(form.get("days") or "14"))
    except ValueError:
        days = 14
    return generate_outreach_package(audience=audience, offer=offer, channels=channels, days=days)
