"""Agent tool: github-agent-sync durable memory bridge."""

from __future__ import annotations

import json
from typing import Any

from keprix.sync.github_bridge import (
    GithubBridgeScope,
    get_status,
    pull_now,
    push_approved_durable_updates,
    search_shared_knowledge,
    write_durable_note,
)
from keprix.tools.registry import registry

TOOLSET = "github-agent-sync"


def _schema() -> dict[str, Any]:
    return {
        "name": "github_agent_sync",
        "description": (
            "Scoped durable knowledge bridge over the agent-sync GitHub repo "
            "(shared with Hermes/Fowler, Carina, Aiva). Actions: status, pull, push, search, note. "
            "Never store secrets. Working memory and chat transcripts are rejected."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["status", "pull", "push", "search", "note"]},
                "scope_kind": {"type": "string", "enum": ["workspace", "user", "shared"]},
                "scope_id": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "number"},
                "path": {"type": "string", "description": "Repo-relative durable note path"},
                "content": {"type": "string"},
                "message": {"type": "string"},
                "push": {"type": "boolean"},
                "product": {"type": "string"},
                "agent": {"type": "string"},
            },
            "required": ["action"],
        },
    }


def _handle(args: dict[str, Any], **_kwargs: Any) -> str:
    action = str(args.get("action") or "")
    scope = GithubBridgeScope(
        scope_kind=args["scope_kind"] if args.get("scope_kind") in {"workspace", "user", "shared"} else "workspace",  # type: ignore[arg-type]
        scope_id=str(args["scope_id"]) if args.get("scope_id") else None,
    )
    if action == "status":
        return json.dumps(get_status(scope))
    if action == "pull":
        return json.dumps(pull_now(scope))
    if action == "push":
        return json.dumps(push_approved_durable_updates({"message": args.get("message")}, scope))
    if action == "search":
        query = str(args.get("query") or "").strip()
        if not query:
            return json.dumps({"error": "query is required"})
        hits = search_shared_knowledge(
            query,
            int(args.get("limit") or 8),
            {"product": str(args.get("product") or ""), "agent": str(args.get("agent") or "")},
            scope,
        )
        return json.dumps({"hits": hits})
    if action == "note":
        path = str(args.get("path") or "").strip()
        content = str(args.get("content") or "")
        if not path or not content.strip():
            return json.dumps({"error": "path and content are required"})
        return json.dumps(
            write_durable_note(
                relative_path=path,
                content=content,
                push=args.get("push") is not False,
                scope=scope,
            )
        )
    return json.dumps({"error": f"unknown action: {action}"})


registry.register(
    name="github_agent_sync",
    toolset=TOOLSET,
    schema=_schema(),
    handler=_handle,
)
