"""Past-chat continuity tools: conversation_search and recent_chats (Prompt 295).

Thin aliases over ``session_search`` with product-namespace isolation.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from tools.registry import registry, tool_error
from tools.session_search_tool import session_search


def _product_isolation_error(profile: Optional[str] = None) -> Optional[str]:
    """Block cross-product profile reads when a product context is active."""
    try:
        from keprix.security.product_context import get_product_context_or_none

        ctx = get_product_context_or_none()
    except Exception:
        return None
    if ctx is None:
        return None
    product_id = (getattr(ctx, "product_id", None) or "").strip()
    if not product_id:
        return None
    # Explicit foreign profile under another product namespace is refused.
    if profile and str(profile).strip():
        prof = str(profile).strip()
        allowed = {
            product_id,
            getattr(ctx, "workspace_id", "") or "",
            getattr(ctx, "tenant_id", "") or "",
        }
        allowed = {a.strip() for a in allowed if a and str(a).strip()}
        if prof not in allowed and prof.lower() != product_id.lower():
            return (
                f"Cross-product session search blocked: profile '{prof}' is "
                f"outside product '{product_id}'."
            )
    return None


def _parse_window(window: str) -> Optional[datetime]:
    """Return a UTC cutoff for natural-language windows, or None for 'all'."""
    text = (window or "").strip().lower()
    if not text or text in {"all", "any", "everything"}:
        return None
    now = datetime.now(timezone.utc)
    if "hour" in text:
        m = re.search(r"(\d+)", text)
        hours = int(m.group(1)) if m else 24
        return now - timedelta(hours=max(1, hours))
    if "yesterday" in text:
        return now - timedelta(days=1)
    if "week" in text:
        m = re.search(r"(\d+)", text)
        weeks = int(m.group(1)) if m else 1
        return now - timedelta(weeks=max(1, weeks))
    if "month" in text:
        return now - timedelta(days=30)
    if "day" in text or "today" in text:
        m = re.search(r"(\d+)", text)
        days = int(m.group(1)) if m else 1
        if "today" in text:
            days = 1
        return now - timedelta(days=max(1, days))
    # Default: last 7 days for unrecognized but non-empty windows.
    return now - timedelta(days=7)


def _filter_sessions_by_cutoff(payload: dict[str, Any], cutoff: datetime) -> dict[str, Any]:
    sessions = payload.get("sessions") or payload.get("results") or []
    if not isinstance(sessions, list):
        return payload
    kept = []
    for item in sessions:
        if not isinstance(item, dict):
            continue
        stamp = item.get("last_active") or item.get("started_at") or ""
        if not stamp:
            kept.append(item)
            continue
        try:
            # Accept ISO-ish timestamps.
            parsed = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed >= cutoff:
                kept.append(item)
        except Exception:
            kept.append(item)
    out = dict(payload)
    if "sessions" in out:
        out["sessions"] = kept
    if "results" in out:
        out["results"] = kept
    out["window_cutoff"] = cutoff.isoformat()
    out["count"] = len(kept)
    return out


def conversation_search_tool(
    query: str = "",
    limit: int = 5,
    profile: str | None = None,
    current_session_id: str | None = None,
    db=None,
) -> str:
    """Topic keyword search across past chats (alias of session_search discovery)."""
    blocked = _product_isolation_error(profile)
    if blocked:
        return tool_error(blocked, success=False)
    if not query or not str(query).strip():
        return tool_error("conversation_search requires a query.", success=False)
    return session_search(
        query=str(query).strip(),
        limit=limit,
        profile=profile,
        current_session_id=current_session_id,
        db=db,
    )


def recent_chats_tool(
    window: str = "last week",
    limit: int = 5,
    profile: str | None = None,
    current_session_id: str | None = None,
    db=None,
) -> str:
    """Time-anchored browse of recent chats (alias of session_search browse)."""
    blocked = _product_isolation_error(profile)
    if blocked:
        return tool_error(blocked, success=False)
    raw = session_search(
        query="",
        limit=limit,
        profile=profile,
        current_session_id=current_session_id,
        db=db,
    )
    try:
        payload = json.loads(raw)
    except Exception:
        return raw
    if not payload.get("success", True) and payload.get("error"):
        return raw
    cutoff = _parse_window(window)
    if cutoff is not None:
        payload = _filter_sessions_by_cutoff(payload, cutoff)
    payload["window"] = window
    payload["tool"] = "recent_chats"
    return json.dumps(payload, ensure_ascii=False)


def check_conversation_search_requirements() -> bool:
    return True


CONVERSATION_SEARCH_SCHEMA = {
    "name": "conversation_search",
    "description": (
        "Search past chats by topic keywords when the user refers to earlier "
        "work (\"the bug we discussed\", \"my project\", \"what you suggested\"). "
        "Prefer this before asking the user to repeat themselves. "
        "Alias of session_search discovery mode."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Topic keywords to find in past chats.",
            },
            "limit": {
                "type": "integer",
                "description": "Max matches (1-10). Default 5.",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

RECENT_CHATS_SCHEMA = {
    "name": "recent_chats",
    "description": (
        "List recent chats in a time window (\"yesterday\", \"last week\", "
        "\"last 3 days\"). Use when the user anchors to time rather than topic."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "window": {
                "type": "string",
                "description": 'Natural-language window, e.g. "yesterday", "last week".',
                "default": "last week",
            },
            "limit": {
                "type": "integer",
                "description": "Max sessions (1-10). Default 5.",
                "default": 5,
            },
        },
        "required": [],
    },
}


registry.register(
    name="conversation_search",
    toolset="session_search",
    schema=CONVERSATION_SEARCH_SCHEMA,
    handler=lambda args, **kw: conversation_search_tool(
        query=args.get("query") or "",
        limit=args.get("limit") or 5,
        profile=args.get("profile"),
        current_session_id=kw.get("session_id"),
    ),
    check_fn=check_conversation_search_requirements,
    emoji="💬",
)

registry.register(
    name="recent_chats",
    toolset="session_search",
    schema=RECENT_CHATS_SCHEMA,
    handler=lambda args, **kw: recent_chats_tool(
        window=args.get("window") or "last week",
        limit=args.get("limit") or 5,
        profile=args.get("profile"),
        current_session_id=kw.get("session_id"),
    ),
    check_fn=check_conversation_search_requirements,
    emoji="🕒",
)
