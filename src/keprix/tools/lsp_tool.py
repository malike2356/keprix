"""Service-gated semantic LSP rename tool.

The language server computes the workspace edit; Keprix owns validation,
staleness checks, and the atomic disk transaction.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agent.lsp import get_service
from agent.lsp.client import uri_to_path
from agent.lsp.workspace import resolve_workspace_for_file
from tools.file_state import get_registry
from tools.registry import registry


def _check_lsp() -> bool:
    service = get_service()
    return service is not None and service.is_active()


def _position_offset(text: str, position: dict[str, Any]) -> int:
    line = int(position.get("line", 0))
    character = int(position.get("character", 0))
    lines = text.splitlines(keepends=True)
    if line < 0 or line >= len(lines):
        raise ValueError(f"line {line} is outside the document")
    prefix = lines[line]
    # LSP positions use UTF-16 code units, not Python code points.
    units = 0
    offset = 0
    for char in prefix:
        if units >= character:
            break
        units += len(char.encode("utf-16-le")) // 2
        offset += 1
    if units < character:
        raise ValueError(f"character {character} is outside line {line}")
    return sum(len(item) for item in lines[:line]) + offset


def _apply_text_edits(text: str, edits: list[dict[str, Any]]) -> str:
    spans: list[tuple[int, int, str]] = []
    for edit in edits:
        rng = edit.get("range") or {}
        start = _position_offset(text, rng.get("start") or {})
        end = _position_offset(text, rng.get("end") or {})
        if end < start:
            raise ValueError("language server returned a reversed text range")
        spans.append((start, end, str(edit.get("newText") or "")))
    spans.sort(key=lambda item: (item[0], item[1]), reverse=True)
    for index in range(len(spans) - 1):
        if spans[index][0] < spans[index + 1][1]:
            raise ValueError("language server returned overlapping text edits")
    for start, end, replacement in spans:
        text = text[:start] + replacement + text[end:]
    return text


def _workspace_edits(result: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    changes: dict[str, list[dict[str, Any]]] = {}
    for uri, edits in (result.get("changes") or {}).items():
        if not isinstance(uri, str) or not isinstance(edits, list):
            raise ValueError("invalid workspace edit changes payload")
        changes[uri] = edits
    for item in result.get("documentChanges") or []:
        if not isinstance(item, dict) or "textDocument" not in item:
            raise ValueError("rename returned unsupported non-text document change")
        document = item.get("textDocument") or {}
        uri = document.get("uri")
        edits = item.get("edits")
        if not isinstance(uri, str) or not isinstance(edits, list):
            raise ValueError("invalid documentChanges text edit")
        changes.setdefault(uri, []).extend(edits)
    return changes


def _rename(args: dict[str, Any], **kwargs: Any) -> str:
    path = os.path.abspath(str(args.get("path") or ""))
    if not path:
        return json.dumps({"ok": False, "error": "path is required"})
    service = get_service()
    if service is None or not service.is_active():
        return json.dumps({"ok": False, "error": "LSP is not configured or enabled"})
    workspace, gated = resolve_workspace_for_file(path)
    if not workspace or not gated or not service.enabled_for(path):
        return json.dumps({"ok": False, "error": "LSP is unavailable for this workspace"})
    task_id = str(kwargs.get("task_id") or "lsp_rename")
    try:
        edit = service.rename_sync(
            path,
            int(args.get("line", 0)),
            int(args.get("character", 0)),
            str(args.get("new_name") or ""),
        )
        by_uri = _workspace_edits(edit)
        if not by_uri:
            return json.dumps({"ok": True, "files_changed": 0, "edits": []})

        from keprix.coding.scoped_replace import apply_edit, replace_exact_block, rollback_edit

        state = get_registry()
        prepared: list[tuple[Path, Any]] = []
        for uri, text_edits in by_uri.items():
            target = Path(uri_to_path(uri)).resolve()
            target.relative_to(Path(workspace).resolve())
            current = target.read_text(encoding="utf-8")
            stale = state.check_stale(task_id, str(target))
            if stale:
                raise RuntimeError(stale)
            updated = _apply_text_edits(current, text_edits)
            prepared.append((target, replace_exact_block(Path(workspace), str(target.relative_to(workspace)), current, updated)))

        applied: list[Any] = []
        try:
            for target, result in prepared:
                if not result.ok:
                    raise RuntimeError(result.error or f"edit failed for {target}")
                apply_edit(result, Path(workspace))
                state.note_write(task_id, str(target))
                applied.append(result)
        except Exception:
            for result in reversed(applied):
                rollback_edit(result, Path(workspace))
            raise
        return json.dumps({
            "ok": True,
            "files_changed": len(applied),
            "edits": [{"path": item.path, "diff": item.diff_preview} for item in applied],
        })
    except Exception as exc:  # tool boundary returns an honest model-facing error
        return json.dumps({"ok": False, "error": str(exc)})


SCHEMA = {
    "name": "lsp_rename",
    "description": "Semantically rename a symbol through the configured language server and atomically apply its workspace edit.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute path to the source file."},
            "line": {"type": "integer", "minimum": 0},
            "character": {"type": "integer", "minimum": 0},
            "new_name": {"type": "string", "description": "New symbol name."},
        },
        "required": ["path", "line", "character", "new_name"],
    },
}

registry.register(
    name="lsp_rename",
    toolset="coding",
    schema=SCHEMA,
    handler=_rename,
    check_fn=_check_lsp,
)
