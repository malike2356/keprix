"""Agent OS glass dashboard: one pane for agents, memory, tasks, tokens."""

from __future__ import annotations

from typing import Any

from keprix.agent_os.workflow_kanban import list_workflow_boards
from keprix.vault.capture import ensure_default_vault
from keprix.vault.config import get_configured_provider, get_vault_config


async def build_glass_dashboard(*, days: int = 7) -> dict[str, Any]:
    """Compose the single-pane Agent OS dashboard payload."""
    vault_section = await _vault_section()
    agents_section = _agents_section()
    tasks_section = _tasks_section()
    tokens_section = await _tokens_section(days=days)

    return {
        "ok": True,
        "days": days,
        "agents": agents_section,
        "memory": vault_section,
        "tasks": tasks_section,
        "tokens": tokens_section,
        "links": {
            "board": "/agent-os",
            "memory_galaxy": "/memory/galaxy",
            "usage": "/usage",
            "agent_runtime": "/agent-runtime",
            "tasks": "/tasks",
            "vault": "/settings/vault",
            "channels": "/dashboard/channels",
        },
    }


async def _vault_section() -> dict[str, Any]:
    try:
        ensure_default_vault()
        config = get_vault_config()
        provider = get_configured_provider()
        graph = await provider.get_graph()
        try:
            top = await provider.list_files("/")
        except FileNotFoundError:
            top = []
        return {
            "configured": bool(config.root_path),
            "root_path": config.root_path,
            "provider": config.provider,
            "file_count_top": len(top),
            "graph_nodes": len(graph.get("nodes") or []),
            "graph_edges": len(graph.get("edges") or []),
        }
    except Exception as exc:
        return {
            "configured": False,
            "root_path": "",
            "provider": "local_folder",
            "file_count_top": 0,
            "graph_nodes": 0,
            "graph_edges": 0,
            "error": str(exc),
        }


def _agents_section() -> dict[str, Any]:
    apps: list[dict[str, Any]] = []
    try:
        from keprix.agent_apps.registry import get_agent_app_registry

        registry = get_agent_app_registry()
        for app in registry.list_apps() if hasattr(registry, "list_apps") else []:
            if isinstance(app, dict):
                apps.append(
                    {
                        "name": app.get("name") or app.get("id"),
                        "display_name": app.get("display_name") or app.get("name"),
                        "runtime": app.get("runtime"),
                        "source": app.get("source"),
                    }
                )
            else:
                apps.append({"name": str(app)})
    except Exception:
        apps = []

    catalog: list[dict[str, Any]] = []
    try:
        from keprix.agent_apps.catalog import list_catalog_templates

        catalog = [
            {
                "id": item.get("id"),
                "display_name": item.get("display_name"),
                "category": item.get("category"),
                "featured": bool(item.get("featured")),
            }
            for item in list_catalog_templates()
        ]
    except Exception:
        catalog = []

    return {
        "installed": apps[:50],
        "installed_count": len(apps),
        "catalog_featured": [item for item in catalog if item.get("featured")][:8],
        "catalog_count": len(catalog),
    }


def _tasks_section() -> dict[str, Any]:
    boards = list_workflow_boards(limit=10)
    open_todo = 0
    open_doing = 0
    done = 0
    for board in boards:
        columns = board.get("columns") or {}
        open_todo += len(columns.get("todo") or [])
        open_doing += len(columns.get("doing") or [])
        done += len(columns.get("done") or [])
    return {
        "workflow_boards": boards,
        "board_count": len(boards),
        "todo": open_todo,
        "doing": open_doing,
        "done": done,
    }


async def _tokens_section(*, days: int) -> dict[str, Any]:
    try:
        from keprix.usage.analytics import get_llm_usage_analytics
        from keprix.usage.filters import UsageQueryFilters

        filters = UsageQueryFilters.from_params(workspace_id="default", days=days)
        analytics = get_llm_usage_analytics()
        summary = await analytics.summary(filters)
        agents = await analytics.breakdown(filters, dimension="agent")
        return {
            "summary": summary,
            "by_agent": agents[:20],
            "efficiency": _efficiency_rows(agents),
        }
    except Exception as exc:
        return {"summary": {}, "by_agent": [], "efficiency": [], "error": str(exc)}


def _efficiency_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        requests = max(1, int(row.get("request_count") or 0))
        tokens = float(row.get("total_tokens") or 0)
        cost = float(row.get("total_cost_usd") or 0)
        out.append(
            {
                "key": row.get("key") or row.get("label") or "unknown",
                "label": row.get("label") or row.get("key") or "unknown",
                "tokens_per_request": round(tokens / requests, 1),
                "cost_per_1k_tokens": round((cost / tokens) * 1000, 4) if tokens else 0.0,
                "request_count": requests,
                "total_tokens": int(tokens),
                "total_cost_usd": cost,
            }
        )
    return out
