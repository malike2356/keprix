"""Agent-facing helpers for the universal markdown vault."""

from __future__ import annotations

import asyncio
from typing import Any

from tools.registry import registry


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        raise RuntimeError("vault tools cannot run inside an active event loop")
    return loop.run_until_complete(coro)


def vault_configured() -> bool:
    from keprix.vault.config import get_vault_config

    return bool(get_vault_config().root_path)


def _document_vault_enabled() -> bool:
    try:
        from keprix.document_vault.flags import load_flags

        return bool(load_flags().enabled)
    except Exception:
        return False


def vault_read(path: str) -> str:
    if _document_vault_enabled():
        raise RuntimeError(
            "Document Vault is enabled. Use document_vault_read / document_vault_inspect "
            "with item_id instead of knowledge-vault host paths."
        )
    from keprix.vault.config import get_configured_provider

    return _run(get_configured_provider().read_file(path))


def vault_write(path: str, content: str) -> dict[str, Any]:
    if _document_vault_enabled():
        return {
            "ok": False,
            "error_code": "migrated",
            "error": (
                "Document Vault is enabled. Use document_vault_create_file / "
                "document_vault_update instead of knowledge-vault path writes."
            ),
        }
    from keprix.vault.config import get_configured_provider, get_vault_config

    if get_vault_config().read_only:
        return {"ok": False, "error": "Vault is read-only"}
    _run(get_configured_provider().write_file(path, content))
    return {"ok": True, "path": path}


def vault_search(query: str) -> dict[str, Any]:
    if _document_vault_enabled():
        return {
            "ok": False,
            "error_code": "migrated",
            "error": "Document Vault is enabled. Use document_vault_search instead.",
            "hint": "document_vault_search",
        }
    from keprix.vault.config import get_configured_provider

    rows = _run(get_configured_provider().search(query))
    return {"results": [row.to_dict() for row in rows]}


registry.register(
    name="vault_read",
    toolset="vault",
    description="Read a markdown file from the configured knowledge vault.",
    emoji="📚",
    requires_env=False,
    check_fn=vault_configured,
    schema={
        "type": "function",
        "function": {
            "name": "vault_read",
            "description": "Read a markdown file from the configured knowledge vault.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    handler=lambda args, **_: vault_read(args["path"]),
)

registry.register(
    name="vault_write",
    toolset="vault",
    description="Write a markdown file to the configured knowledge vault.",
    emoji="✍️",
    requires_env=False,
    check_fn=vault_configured,
    schema={
        "type": "function",
        "function": {
            "name": "vault_write",
            "description": "Write a markdown file to the configured knowledge vault.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    handler=lambda args, **_: vault_write(args["path"], args["content"]),
)

registry.register(
    name="vault_search",
    toolset="vault",
    description="Search markdown files in the configured knowledge vault.",
    emoji="🔎",
    requires_env=False,
    check_fn=vault_configured,
    schema={
        "type": "function",
        "function": {
            "name": "vault_search",
            "description": "Search markdown files in the configured knowledge vault.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    handler=lambda args, **_: vault_search(args["query"]),
)
