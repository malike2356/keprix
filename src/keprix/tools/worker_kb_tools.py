"""Keprix tools: worker knowledge base (K03)."""

from __future__ import annotations

import json
from typing import Any

from tools.registry import registry

TOOLSET = "worker_kb"


def check_worker_kb_requirements() -> bool:
    return True


def _ok(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _err(message: str, **extra: Any) -> str:
    return json.dumps({"error": message, **extra}, ensure_ascii=False)


def _run(coro):
    from keprix.worker_kb.service import _run_async

    return _run_async(coro)


def _svc():
    from keprix.worker_kb.service import get_worker_kb_service

    return get_worker_kb_service()


def kb_add_entry(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    worker_id = str(args.get("worker_id") or "").strip()
    content = str(args.get("content") or "")
    if not workspace_id or not worker_id or not content.strip():
        return _err("workspace_id, worker_id, and content are required")
    try:
        result = _run(
            _svc().add_entry(
                workspace_id,
                worker_id,
                content=content,
                entry_type=str(args.get("entry_type") or "faq"),
                title=args.get("title"),
                source=str(args.get("source") or "manual"),
                source_file=args.get("source_file"),
                kb_name=str(args.get("kb_name") or "Default"),
            )
        )
    except ValueError as exc:
        return _err(str(exc))
    return _ok(result)


def kb_search(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    worker_id = str(args.get("worker_id") or "").strip()
    query = str(args.get("query") or args.get("q") or "")
    if not workspace_id or not worker_id or not query.strip():
        return _err("workspace_id, worker_id, and query are required")
    limit = int(args.get("limit") or 5)
    result = _run(_svc().search(workspace_id, worker_id, query, limit=limit))
    return _ok(result)


def kb_list_entries(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    worker_id = str(args.get("worker_id") or "").strip()
    if not workspace_id or not worker_id:
        return _err("workspace_id and worker_id are required")
    enabled_only = bool(args.get("enabled_only"))
    return _ok(_svc().list_entries(workspace_id, worker_id, enabled_only=enabled_only))


def kb_delete_entry(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    worker_id = str(args.get("worker_id") or "").strip()
    entry_id = str(args.get("entry_id") or "").strip()
    if not workspace_id or not worker_id or not entry_id:
        return _err("workspace_id, worker_id, and entry_id are required")
    try:
        result = _run(_svc().delete_entry(workspace_id, worker_id, entry_id))
    except (LookupError, PermissionError) as exc:
        return _err(str(exc))
    return _ok(result)


def kb_toggle_entry(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    worker_id = str(args.get("worker_id") or "").strip()
    entry_id = str(args.get("entry_id") or "").strip()
    if not workspace_id or not worker_id or not entry_id:
        return _err("workspace_id, worker_id, and entry_id are required")
    enabled = args.get("enabled")
    try:
        result = _run(
            _svc().toggle_entry(
                workspace_id,
                worker_id,
                entry_id,
                enabled=None if enabled is None else bool(enabled),
            )
        )
    except (LookupError, PermissionError) as exc:
        return _err(str(exc))
    return _ok(result)


def kb_get_context(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    worker_id = str(args.get("worker_id") or "").strip()
    if not workspace_id or not worker_id:
        return _err("workspace_id and worker_id are required")
    max_chars = int(args.get("max_chars") or 8000)
    return _ok(_svc().get_context(workspace_id, worker_id, max_chars=max_chars))


registry.register(
    name="kb_add_entry",
    toolset=TOOLSET,
    schema={
        "name": "kb_add_entry",
        "description": "Add a document, FAQ, or instruction to a worker knowledge base (chunked + embedded).",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "worker_id": {"type": "string"},
                "content": {"type": "string"},
                "entry_type": {"type": "string", "enum": ["document", "faq", "instruction"]},
                "title": {"type": "string"},
                "source": {"type": "string"},
                "source_file": {"type": "string"},
                "kb_name": {"type": "string"},
            },
            "required": ["workspace_id", "worker_id", "content"],
        },
    },
    handler=kb_add_entry,
    check_fn=check_worker_kb_requirements,
)

registry.register(
    name="kb_search",
    toolset=TOOLSET,
    schema={
        "name": "kb_search",
        "description": "Semantic search across a worker knowledge base (top chunks).",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "worker_id": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["workspace_id", "worker_id", "query"],
        },
    },
    handler=kb_search,
    check_fn=check_worker_kb_requirements,
)

registry.register(
    name="kb_list_entries",
    toolset=TOOLSET,
    schema={
        "name": "kb_list_entries",
        "description": "List knowledge entries for a worker.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "worker_id": {"type": "string"},
                "enabled_only": {"type": "boolean"},
            },
            "required": ["workspace_id", "worker_id"],
        },
    },
    handler=kb_list_entries,
    check_fn=check_worker_kb_requirements,
)

registry.register(
    name="kb_delete_entry",
    toolset=TOOLSET,
    schema={
        "name": "kb_delete_entry",
        "description": "Delete a worker knowledge entry and its embeddings.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "worker_id": {"type": "string"},
                "entry_id": {"type": "string"},
            },
            "required": ["workspace_id", "worker_id", "entry_id"],
        },
    },
    handler=kb_delete_entry,
    check_fn=check_worker_kb_requirements,
)

registry.register(
    name="kb_toggle_entry",
    toolset=TOOLSET,
    schema={
        "name": "kb_toggle_entry",
        "description": "Enable or disable a knowledge entry (disabled entries leave search).",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "worker_id": {"type": "string"},
                "entry_id": {"type": "string"},
                "enabled": {"type": "boolean"},
            },
            "required": ["workspace_id", "worker_id", "entry_id"],
        },
    },
    handler=kb_toggle_entry,
    check_fn=check_worker_kb_requirements,
)

registry.register(
    name="kb_get_context",
    toolset=TOOLSET,
    schema={
        "name": "kb_get_context",
        "description": "Get all enabled worker KB entries as a formatted context string.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "worker_id": {"type": "string"},
                "max_chars": {"type": "integer"},
            },
            "required": ["workspace_id", "worker_id"],
        },
    },
    handler=kb_get_context,
    check_fn=check_worker_kb_requirements,
)
