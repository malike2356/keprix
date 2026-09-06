"""Small durable notes surface for worker agents."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.tools.registry import registry


def _path(workspace_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(workspace_id or "default"))[:80] or "default"
    root = Path.home() / ".keprix" / "workspace-notes"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{safe}.json"


def _read(workspace_id: str) -> list[dict[str, Any]]:
    path = _path(workspace_id)
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _write(workspace_id: str, rows: list[dict[str, Any]]) -> None:
    path = _path(workspace_id)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    temporary.replace(path)


def workspace_notes_list(args: dict[str, Any]) -> str:
    return json.dumps(_read(str(args.get("workspace_id") or "default")))


def workspace_notes_create(args: dict[str, Any]) -> str:
    workspace_id = str(args.get("workspace_id") or "default")
    title = str(args.get("title") or "").strip()
    body = str(args.get("body") or "")
    if not title or not body.strip():
        return json.dumps({"status": "invalid", "reason": "title and body are required"})
    note = {"id": "note-" + uuid.uuid4().hex[:12], "title": title, "body": body, "tags": list(args.get("tags") or []), "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
    rows = _read(workspace_id)
    rows.insert(0, note)
    _write(workspace_id, rows)
    return json.dumps(note)


def workspace_notes_update(args: dict[str, Any]) -> str:
    workspace_id = str(args.get("workspace_id") or "default")
    note_id = str(args.get("note_id") or "")
    rows = _read(workspace_id)
    for note in rows:
        if note["id"] == note_id:
            for key in ("title", "body", "tags"):
                if key in args:
                    note[key] = args[key]
            note["updated_at"] = datetime.now(timezone.utc).isoformat()
            _write(workspace_id, rows)
            return json.dumps(note)
    return json.dumps({"status": "not_found"})


def workspace_notes_delete(args: dict[str, Any]) -> str:
    workspace_id = str(args.get("workspace_id") or "default")
    note_id = str(args.get("note_id") or "")
    rows = _read(workspace_id)
    kept = [note for note in rows if note["id"] != note_id]
    if len(kept) == len(rows):
        return json.dumps({"ok": False, "status": "not_found"})
    _write(workspace_id, kept)
    return json.dumps({"ok": True, "status": "deleted"})


_BASE = {"type": "object", "properties": {"workspace_id": {"type": "string"}}}
registry.register(name="workspace_notes_list", toolset="productivity", schema={"name": "workspace_notes_list", "description": "List durable notes for a workspace.", "parameters": _BASE}, handler=workspace_notes_list)
registry.register(name="workspace_notes_create", toolset="productivity", schema={"name": "workspace_notes_create", "description": "Create a durable workspace note.", "parameters": {"type": "object", "properties": {**_BASE["properties"], "title": {"type": "string"}, "body": {"type": "string"}, "tags": {"type": "array"}}, "required": ["title", "body"]}}, handler=workspace_notes_create)
registry.register(name="workspace_notes_update", toolset="productivity", schema={"name": "workspace_notes_update", "description": "Update a workspace note.", "parameters": {"type": "object", "properties": {**_BASE["properties"], "note_id": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}, "tags": {"type": "array"}}, "required": ["note_id"]}}, handler=workspace_notes_update)
registry.register(name="workspace_notes_delete", toolset="productivity", schema={"name": "workspace_notes_delete", "description": "Delete a workspace note.", "parameters": {"type": "object", "properties": {**_BASE["properties"], "note_id": {"type": "string"}}, "required": ["note_id"]}}, handler=workspace_notes_delete)
