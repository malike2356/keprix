"""MCP / integration connector-first routing (Prompt 296).

Prefer connected connectors over browser scraping. Suggest connect for
catalogued but disconnected servers. Never invent fake MCP outputs.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional, Sequence

logger = logging.getLogger(__name__)

BROWSER_TOOLS = frozenset(
    {
        "web_search",
        "web_extract",
        "browser_navigate",
        "browser_snapshot",
        "browser_click",
        "browser_type",
        "browser_scroll",
        "browser_back",
        "browser_press",
        "browser_get_images",
        "browser_vision",
        "browser_console",
        "browser_cdp",
        "browser_dialog",
    }
)

# Intent categories -> keyword / tool-name hints.
CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "calendar": ("calendar", "schedule", "meeting", "event", "gws_calendar", "ical"),
    "email": ("email", "gmail", "inbox", "mail", "gws_gmail", "smtp"),
    "drive": ("drive", "docs", "document", "spreadsheet", "gws_drive", "gws_sheets", "files"),
    "issues": ("github", "issue", "pull request", "pr ", "jira", "linear", "bug tracker"),
    "chat": ("slack", "discord", "teams message", "chat channel"),
    "crm": ("crm", "salesforce", "hubspot", "pipedrive", "lead"),
    "docs": ("notion", "wiki", "notes", "confluence"),
    "tasks": ("trello", "kanban", "todoist", "asana", "task board"),
}

THIRD_PARTY_MCP_TAG = "[third_party_mcp_app]"


class ConnectorRouteAction(str, Enum):
    USE_CONNECTED = "use_connected"
    SUGGEST_CONNECT = "suggest_connect"
    ALLOW_BROWSER = "allow_browser"
    BYPASS = "bypass"


@dataclass(frozen=True)
class ConnectorRouteDecision:
    action: ConnectorRouteAction
    category: str = ""
    connected_tools: tuple[str, ...] = ()
    suggest_ids: tuple[str, ...] = ()
    message: str = ""
    connect_urls: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "category": self.category,
            "connected_tools": list(self.connected_tools),
            "suggest_ids": list(self.suggest_ids),
            "message": self.message,
            "connect_urls": list(self.connect_urls),
        }


@dataclass
class ConnectorRouter:
    """Decide connector vs browser for a user intent / tool call."""

    available_tool_names: Sequence[str] = field(default_factory=tuple)
    force_browser: bool = False

    def detect_category(self, text: str) -> str:
        hay = (text or "").lower()
        if not hay:
            return ""
        scores: list[tuple[int, str]] = []
        for category, hints in CATEGORY_HINTS.items():
            score = sum(1 for hint in hints if hint in hay)
            if score:
                scores.append((score, category))
        if not scores:
            return ""
        scores.sort(key=lambda item: (-item[0], item[1]))
        return scores[0][1]

    def connected_tools_for(self, category: str) -> list[str]:
        if not category:
            return []
        hints = CATEGORY_HINTS.get(category, ())
        names = list(self.available_tool_names) or self._registry_tool_names()
        matched: list[str] = []
        for name in names:
            lower = name.lower()
            # Built-in Google Workspace tools and MCP-prefixed tools.
            if category == "calendar" and "calendar" in lower:
                matched.append(name)
            elif category == "email" and ("gmail" in lower or "email" in lower or "mail" in lower):
                matched.append(name)
            elif category == "drive" and ("drive" in lower or "sheets" in lower or "docs" in lower):
                matched.append(name)
            elif any(h.replace(" ", "_") in lower or h in lower for h in hints):
                if lower.startswith("mcp_") or lower.startswith("gws_") or any(
                    h in lower for h in ("notion", "trello", "slack", "github")
                ):
                    matched.append(name)
        # De-dupe preserve order.
        seen: set[str] = set()
        out: list[str] = []
        for name in matched:
            if name not in seen:
                seen.add(name)
                out.append(name)
        return out

    def catalog_matches(self, category: str, query: str = "") -> list[dict[str, Any]]:
        """Return catalogued connectors that fit but may not be connected."""
        try:
            from keprix.integrations.connector_catalog import (
                catalog_install_status,
                load_connector_catalog,
            )
        except Exception as exc:
            logger.debug("connector catalog unavailable: %s", exc)
            return []

        query_tokens = [t for t in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(t) > 2]
        results: list[dict[str, Any]] = []
        for entry in load_connector_catalog():
            blob = " ".join(
                [
                    entry.id,
                    entry.label,
                    entry.description,
                    entry.category,
                    " ".join(entry.tags),
                ]
            ).lower()
            score = 0
            if category and (
                category in blob
                or any(h in blob for h in CATEGORY_HINTS.get(category, ()))
            ):
                score += 2
            if query_tokens:
                score += sum(1 for tok in query_tokens if tok in blob)
            elif query and query.lower() in blob:
                score += 1
            if score <= 0:
                continue
            status = catalog_install_status(entry.id)
            installed = bool(status.get("installed"))
            enabled = status.get("enabled", installed)
            results.append(
                {
                    **entry.to_dict(),
                    "installed": installed,
                    "enabled": bool(enabled),
                    "connect_url": connect_url_for(entry.id, entry.auth_pattern),
                    "score": score,
                }
            )
        results.sort(
            key=lambda row: (
                bool(row.get("installed") and row.get("enabled")),
                -int(row.get("score") or 0),
                row.get("label", ""),
            )
        )
        return results

    def route(
        self,
        *,
        text: str = "",
        tool_name: str = "",
        force_browser: bool | None = None,
    ) -> ConnectorRouteDecision:
        use_force = self.force_browser if force_browser is None else force_browser
        if use_force:
            return ConnectorRouteDecision(
                action=ConnectorRouteAction.BYPASS,
                message="Browser forced by operator/user.",
            )

        category = self.detect_category(text) or self.detect_category(tool_name)
        if not category and tool_name not in BROWSER_TOOLS:
            return ConnectorRouteDecision(action=ConnectorRouteAction.BYPASS)

        connected = self.connected_tools_for(category) if category else []
        if connected:
            self._emit_scout("connector.used", category, connected[:5])
            return ConnectorRouteDecision(
                action=ConnectorRouteAction.USE_CONNECTED,
                category=category,
                connected_tools=tuple(connected[:12]),
                message=(
                    f"Use connected connector tools for {category} before the browser: "
                    + ", ".join(connected[:8])
                ),
            )

        catalog = self.catalog_matches(category, text) if category else []
        suggest = [
            row for row in catalog
            if not (row.get("installed") and row.get("enabled"))
        ][:5]
        if suggest:
            ids = tuple(str(row["id"]) for row in suggest)
            urls = tuple(str(row.get("connect_url") or "") for row in suggest if row.get("connect_url"))
            self._emit_scout("connector.suggested", category, list(ids))
            return ConnectorRouteDecision(
                action=ConnectorRouteAction.SUGGEST_CONNECT,
                category=category,
                suggest_ids=ids,
                connect_urls=urls,
                message=(
                    f"No connected {category} connector. Call suggest_connectors "
                    f"with ids={list(ids)} before scraping the web."
                ),
            )

        return ConnectorRouteDecision(
            action=ConnectorRouteAction.ALLOW_BROWSER,
            category=category,
            message="No connector fit; browser/web tools are allowed.",
        )

    def before_browser_tool(
        self,
        tool_name: str,
        args: dict[str, Any] | None = None,
    ) -> Optional[str]:
        """Return a JSON error string when browser should yield to connectors."""
        if tool_name not in BROWSER_TOOLS:
            return None
        args = args or {}
        text = " ".join(
            str(args.get(key) or "")
            for key in ("query", "search_term", "url", "prompt", "goal", "text")
        )
        decision = self.route(text=text, tool_name=tool_name)
        if decision.action == ConnectorRouteAction.USE_CONNECTED:
            return json.dumps(
                {
                    "error": decision.message,
                    "connector_first": True,
                    "action": decision.action.value,
                    "connected_tools": list(decision.connected_tools),
                    "category": decision.category,
                },
                ensure_ascii=False,
            )
        if decision.action == ConnectorRouteAction.SUGGEST_CONNECT:
            return json.dumps(
                {
                    "error": decision.message,
                    "connector_first": True,
                    "action": decision.action.value,
                    "suggest_ids": list(decision.suggest_ids),
                    "connect_urls": list(decision.connect_urls),
                    "category": decision.category,
                    "hint": "Call search_mcp_registry then suggest_connectors; do not scrape.",
                },
                ensure_ascii=False,
            )
        return None

    @staticmethod
    def _registry_tool_names() -> list[str]:
        try:
            from tools.registry import registry

            return list(registry.list_tools() or [])
        except Exception:
            return []

    @staticmethod
    def _emit_scout(action: str, category: str, targets: Iterable[str]) -> None:
        try:
            from keprix.security.scout_integration import emit_scout_signal
            from keprix.security.scout_types import SignalCategory, SignalSeverity

            emit_scout_signal(
                SignalCategory.GOVERNANCE,
                SignalSeverity.INFO,
                action,
                f"category:{category or 'unknown'}",
                {"category": category, "targets": list(targets)},
            )
        except Exception:
            pass


def connect_url_for(connector_id: str, auth_pattern: str = "") -> str:
    if connector_id in {"google-workspace", "gmail", "google_drive", "calendar"} or auth_pattern == "oauth":
        if connector_id.startswith("google") or connector_id in {"gmail", "calendar"}:
            return "/settings/integrations/google-workspace"
    return f"/integrations?id={connector_id}"


def tag_mcp_description(description: str, *, server_name: str = "") -> str:
    """Prefix third-party MCP tool descriptions for model clarity."""
    text = (description or "").strip()
    if THIRD_PARTY_MCP_TAG in text:
        return text
    prefix = f"{THIRD_PARTY_MCP_TAG} "
    if server_name:
        prefix += f"(server={server_name}) "
    return prefix + (text or "Third-party MCP tool")


def apply_connector_first_gate(
    agent: Any,
    tool_name: str,
    args: dict[str, Any] | None = None,
) -> Optional[str]:
    """Executor hook: soft-block browser when a connector should win.

    Operator policy (Prompt 297): ``third_party_mcp=never`` (strict) still
    prefers connected first-party connectors but does not auto-call or nudge
    third-party MCP registry installs. Profiles with ``suggest`` keep soft
    browser gating and connect suggestions.
    """
    if not bool(getattr(agent, "_connector_first", True)):
        return None
    if getattr(agent, "_connector_first_force_browser", False):
        return None

    third_party = "suggest"
    try:
        from keprix.security.operator_policy import get_operator_policy

        policy = getattr(agent, "_operator_policy", None) or get_operator_policy(agent=agent)
        third_party = policy.knobs.third_party_mcp
    except Exception:
        pass

    names = getattr(agent, "valid_tool_names", None) or ()
    router = ConnectorRouter(available_tool_names=list(names))

    # Strict: never suggest third-party MCP connect; still soft-block when a
    # connected connector already exists.
    if third_party == "never":
        if tool_name not in BROWSER_TOOLS:
            return None
        args = args or {}
        text = " ".join(
            str(args.get(key) or "")
            for key in ("query", "search_term", "url", "prompt", "goal", "text")
        )
        decision = router.route(text=text, tool_name=tool_name)
        if decision.action == ConnectorRouteAction.USE_CONNECTED:
            return json.dumps(
                {
                    "error": decision.message,
                    "connector_first": True,
                    "action": decision.action.value,
                    "connected_tools": list(decision.connected_tools),
                    "category": decision.category,
                    "operator_policy": "strict",
                },
                ensure_ascii=False,
            )
        return None

    return router.before_browser_tool(tool_name, args)
