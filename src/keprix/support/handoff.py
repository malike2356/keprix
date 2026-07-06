"""Human handoff hooks with privacy controls."""

from __future__ import annotations

from typing import Any

from keprix.support.diagnostics import build_diagnostics_bundle
from keprix.support.store import get_support_store


async def create_handoff(
    *,
    category: str,
    summary: str,
    privacy: str = "minimal",
    contact_email: str | None = None,
    user_id: str = "admin",
) -> dict[str, Any]:
    store = get_support_store()
    settings = store.get_privacy_settings()
    payload: dict[str, Any] = {
        "category": category,
        "summary": summary,
        "privacy": privacy,
        "user_id": user_id,
        "contact_email": None,
        "diagnostics": None,
    }

    if contact_email and settings.get("allow_contact_email", True):
        payload["contact_email"] = contact_email

    if privacy == "standard" and settings.get("allow_diagnostics_in_handoff", True):
        payload["diagnostics"] = await build_diagnostics_bundle()

    record = store.append_handoff(payload)
    return record
