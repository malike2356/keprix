"""Concierge persona prompt overlay (Prompt 628)."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from keprix.customer_concierge.models import ConciergeProfile

_concierge_ctx: ContextVar[tuple[str, str] | None] = ContextVar("concierge_ctx", default=None)


def set_concierge_prompt_context(workspace_id: str, persona_id: str) -> None:
    _concierge_ctx.set((workspace_id, persona_id))


def clear_concierge_prompt_context() -> None:
    _concierge_ctx.set(None)


def format_business_hours(hours: dict[str, Any] | None) -> str:
    if not hours or not hours.get("windows"):
        return "not configured"
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    parts = []
    for w in hours.get("windows") or []:
        day = day_names[int(w.get("dayOfWeek", 0)) % 7]
        parts.append(f"{day} {w.get('start')}-{w.get('end')}")
    tz = hours.get("timezone") or "UTC"
    return f"{', '.join(parts)} ({tz})"


def build_concierge_persona_overlay(profile: ConciergeProfile) -> str:
    persona = (profile.persona_name or "").strip() or "Concierge"
    business = (profile.business_name or "").strip() or "the business"
    description = (profile.business_description or "").strip()
    escalation = (profile.escalation_email or "").strip() or "the business owner"
    knowledge_ids = ", ".join(profile.knowledge_source_ids) if profile.knowledge_source_ids else "(none configured)"
    hours = format_business_hours(profile.business_hours)
    greeting = (profile.greeting_message or "").strip()

    return f"""
You are {persona}, representing {business}.
{description}

Visitor greeting: {greeting or "(none)"}

Published knowledge boundary:
- Only answer from published knowledge source IDs: {knowledge_ids}.
- Do not use private workspace chat, files, notes, secrets, billing, admin tools, or unpublished drafts.
- If you lack an approved source, say you do not know and offer escalation.

Rules:
- Never share internal workspace information or owner conversations.
- Business hours: {hours}. Outside these hours, tell the visitor when you will be available.
- For issues you cannot resolve, escalate to {escalation}.
- Prefer ICS calendar fallback when no online calendar provider is connected.
""".strip()


def render_registered_concierge_layer() -> str:
    """Zero-arg product layer renderer; uses contextvar when set."""
    ctx = _concierge_ctx.get()
    if not ctx:
        return ""
    workspace_id, persona_id = ctx
    try:
        from keprix.customer_concierge.store import get_concierge_store

        profile = get_concierge_store().get(workspace_id, persona_id)
        if not profile or not profile.published:
            return ""
        return build_concierge_persona_overlay(profile)
    except Exception:
        return ""


def ensure_prompt_layer_registered() -> None:
    from keprix.registries.product_hooks import register_product_prompt_layer

    register_product_prompt_layer(
        "customer_concierge",
        "keprix",
        render_registered_concierge_layer,
    )
