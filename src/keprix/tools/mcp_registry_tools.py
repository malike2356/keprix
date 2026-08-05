"""MCP registry search and connector suggest tools (Prompt 296)."""

from __future__ import annotations

import json
from typing import Any

from agent.connector_router import ConnectorRouter, connect_url_for
from tools.registry import registry, tool_error


def search_mcp_registry_tool(
    query: str = "",
    category: str = "",
    include_installed: bool = False,
) -> str:
    """Find catalogued connectors / MCP servers (connected or not)."""
    q = (query or "").strip()
    cat = (category or "").strip().lower()
    if not q and not cat:
        return tool_error("search_mcp_registry requires query or category.")

    router = ConnectorRouter()
    if not cat:
        cat = router.detect_category(q)
    matches = router.catalog_matches(cat, q)
    if not include_installed:
        matches = [
            row for row in matches
            if not (row.get("installed") and row.get("enabled"))
        ]

    # Also surface MCP catalog entries when available.
    mcp_extra: list[dict[str, Any]] = []
    try:
        from keprix_cli.mcp_catalog import is_enabled, is_installed, list_catalog

        for entry in list_catalog() or []:
            name = getattr(entry, "name", None) or (entry.get("name") if isinstance(entry, dict) else "")
            desc = getattr(entry, "description", None) or (
                entry.get("description") if isinstance(entry, dict) else ""
            )
            if not name:
                continue
            blob = f"{name} {desc}".lower()
            if q and q.lower() not in blob and (not cat or cat not in blob):
                continue
            installed = bool(is_installed(name))
            enabled = bool(is_enabled(name))
            if not include_installed and installed and enabled:
                continue
            mcp_extra.append(
                {
                    "id": name,
                    "label": name,
                    "description": desc or "",
                    "category": cat or "mcp",
                    "auth_pattern": "mcp",
                    "installed": installed,
                    "enabled": enabled,
                    "connect_url": "/admin/mcp",
                    "source": "mcp_catalog",
                }
            )
    except Exception:
        pass

    # De-dupe by id.
    seen: set[str] = set()
    combined: list[dict[str, Any]] = []
    for row in matches + mcp_extra:
        cid = str(row.get("id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        combined.append(row)

    return json.dumps(
        {
            "success": True,
            "query": q,
            "category": cat,
            "matches": combined[:20],
            "count": len(combined[:20]),
            "hint": (
                "Call suggest_connectors with chosen ids to prompt the user "
                "to connect. Do not invent fake MCP UIs or simulated outputs."
            ),
        },
        ensure_ascii=False,
    )


def suggest_connectors_tool(ids: list[str] | None = None, id: str | None = None) -> str:
    """Emit one-click connect suggestions for catalogued connectors."""
    raw: list[str] = []
    if isinstance(ids, list):
        raw.extend(str(x) for x in ids if x)
    if id:
        raw.append(str(id))
    # De-dupe
    seen: set[str] = set()
    ordered: list[str] = []
    for item in raw:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    if not ordered:
        return tool_error("suggest_connectors requires ids or id.")

    suggestions: list[dict[str, Any]] = []
    try:
        from keprix.integrations.connector_catalog import (
            catalog_install_status,
            get_connector,
        )
    except Exception:
        get_connector = None  # type: ignore
        catalog_install_status = None  # type: ignore

    for cid in ordered:
        entry = get_connector(cid) if get_connector else None
        if entry is not None:
            status = catalog_install_status(cid) if catalog_install_status else {}
            suggestions.append(
                {
                    "id": entry.id,
                    "label": entry.label,
                    "description": entry.description,
                    "connect_url": connect_url_for(entry.id, entry.auth_pattern),
                    "installed": bool(status.get("installed")),
                    "enabled": bool(status.get("enabled", status.get("installed"))),
                }
            )
        else:
            suggestions.append(
                {
                    "id": cid,
                    "label": cid,
                    "description": "MCP / catalog connector",
                    "connect_url": "/admin/mcp" if not cid.startswith("google") else "/settings/integrations/google-workspace",
                    "installed": False,
                    "enabled": False,
                }
            )

    try:
        from keprix.security.scout_integration import emit_scout_signal
        from keprix.security.scout_types import SignalCategory, SignalSeverity

        emit_scout_signal(
            SignalCategory.GOVERNANCE,
            SignalSeverity.INFO,
            "connector.suggested",
            f"connectors:{','.join(ordered[:8])}",
            {"ids": ordered, "count": len(suggestions)},
        )
    except Exception:
        pass

    return json.dumps(
        {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions),
            "message": (
                "Ask the user to connect one of these connectors, then use the "
                "connected tools. Do not scrape or invent MCP outputs."
            ),
            "ui": {
                "chip": "suggest_connectors",
                "connectors": [
                    {"id": s["id"], "label": s["label"], "href": s["connect_url"]}
                    for s in suggestions
                ],
            },
        },
        ensure_ascii=False,
    )


def check_mcp_registry_requirements() -> bool:
    return True


SEARCH_MCP_REGISTRY_SCHEMA = {
    "name": "search_mcp_registry",
    "description": (
        "Search the connector / MCP registry for apps that fit a task "
        "(calendar, email, drive, issues, chat, crm). Prefer this over the "
        "browser when a connector category matches. Returns connect URLs for "
        "disconnected servers."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Free-text search (e.g. gmail, notion)."},
            "category": {
                "type": "string",
                "description": "Optional category: calendar, email, drive, issues, chat, crm, docs, tasks.",
            },
            "include_installed": {
                "type": "boolean",
                "description": "Include already connected connectors. Default false.",
                "default": False,
            },
        },
        "required": [],
    },
}

SUGGEST_CONNECTORS_SCHEMA = {
    "name": "suggest_connectors",
    "description": (
        "Prompt the user to connect one or more catalogued connectors "
        "(one-click / deep link). Use after search_mcp_registry when the "
        "needed app is not connected. Do not call third-party MCP tools "
        "until connected."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Connector ids from search_mcp_registry.",
            },
            "id": {
                "type": "string",
                "description": "Single connector id alias.",
            },
        },
        "required": [],
    },
}


registry.register(
    name="search_mcp_registry",
    toolset="mcp_registry",
    schema=SEARCH_MCP_REGISTRY_SCHEMA,
    handler=lambda args, **kw: search_mcp_registry_tool(
        query=args.get("query") or "",
        category=args.get("category") or "",
        include_installed=bool(args.get("include_installed", False)),
    ),
    check_fn=check_mcp_registry_requirements,
    emoji="🔌",
)

registry.register(
    name="suggest_connectors",
    toolset="mcp_registry",
    schema=SUGGEST_CONNECTORS_SCHEMA,
    handler=lambda args, **kw: suggest_connectors_tool(
        ids=args.get("ids"),
        id=args.get("id"),
    ),
    check_fn=check_mcp_registry_requirements,
    emoji="🔗",
)
