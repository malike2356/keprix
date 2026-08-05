"""present_files tool: register outputs as session downloadable attachments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.deliverable_paths import (
    DeliverableZone,
    is_presentable,
    layout_for_path,
    register_presented_files,
    resolve_deliverable_layout,
)
from tools.registry import registry, tool_error


def present_files_tool(
    paths: list[str] | None = None,
    path: str | None = None,
    title: str = "",
    session_id: str = "",
) -> str:
    """Present one or more files under outputs_dir as user-visible attachments."""
    raw_paths: list[str] = []
    if isinstance(paths, list):
        raw_paths.extend(str(p) for p in paths if p)
    if path:
        raw_paths.append(str(path))
    # De-dupe while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for item in raw_paths:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)

    if not ordered:
        return tool_error("present_files requires at least one path under outputs.")

    layout = resolve_deliverable_layout(session_id or None)
    # Prefer layout inferred from the first absolute path so callers do not
    # need to share cwd with the tool process.
    for raw in ordered:
        inferred = layout_for_path(raw)
        if inferred is not None:
            layout = inferred
            break
    accepted: list[Path] = []
    rejected: list[dict[str, str]] = []

    for raw in ordered:
        candidate = Path(raw).expanduser()
        try:
            resolved = candidate.resolve(strict=False)
        except (OSError, RuntimeError, ValueError) as exc:
            rejected.append({"path": raw, "reason": f"invalid path: {exc}"})
            continue

        zone = layout.zone_for(resolved)
        if zone == DeliverableZone.SCRATCH:
            rejected.append(
                {
                    "path": str(resolved),
                    "reason": (
                        "scratch paths are not presentable; copy to "
                        f"{layout.outputs_dir} first, then call present_files"
                    ),
                }
            )
            continue
        if zone == DeliverableZone.UPLOADS:
            rejected.append(
                {
                    "path": str(resolved),
                    "reason": (
                        "uploads are not presentable as finals; copy to "
                        f"{layout.outputs_dir} first"
                    ),
                }
            )
            continue
        if not is_presentable(resolved, layout):
            if not resolved.is_file():
                rejected.append({"path": str(resolved), "reason": "file not found"})
            else:
                rejected.append(
                    {
                        "path": str(resolved),
                        "reason": (
                            "only files under outputs_dir can be presented "
                            f"({layout.outputs_dir})"
                        ),
                    }
                )
            continue
        accepted.append(resolved)

    if not accepted:
        return json.dumps(
            {
                "success": False,
                "error": "No presentable outputs paths.",
                "rejected": rejected,
                "outputs_dir": str(layout.outputs_dir),
                "scratch_dir": str(layout.scratch_dir),
            },
            ensure_ascii=False,
        )

    recorded = register_presented_files(accepted, layout=layout, title=title)
    abs_paths = [str(p) for p in accepted]
    media_tags = [f"MEDIA:{p}" for p in abs_paths]
    payload: dict[str, Any] = {
        "success": True,
        "presented": recorded,
        "paths": abs_paths,
        "path": abs_paths[0],
        "count": len(abs_paths),
        "outputs_dir": str(layout.outputs_dir),
        "session_id": layout.session_id,
        "media": " ".join(media_tags),
        "message": (
            f"Presented {len(abs_paths)} file(s) from outputs. "
            + " ".join(media_tags)
        ),
    }
    if rejected:
        payload["rejected"] = rejected
    if title:
        payload["title"] = title
    return json.dumps(payload, ensure_ascii=False)


def check_present_files_requirements() -> bool:
    return True


PRESENT_FILES_SCHEMA = {
    "name": "present_files",
    "description": (
        "Register final deliverable files so the user can open/download them. "
        "Only paths under the session outputs directory are accepted. "
        "Scratch and uploads paths are refused; copy finals to outputs first. "
        "Call this after writing short files directly to outputs, or after "
        "copying long scratch work into outputs."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "One or more absolute or relative paths under outputs.",
            },
            "path": {
                "type": "string",
                "description": "Single outputs path (alias for paths=[path]).",
            },
            "title": {
                "type": "string",
                "description": "Optional display title for the attachment chip.",
            },
        },
        "required": [],
    },
}


registry.register(
    name="present_files",
    toolset="file",
    schema=PRESENT_FILES_SCHEMA,
    handler=lambda args, **kw: present_files_tool(
        paths=args.get("paths"),
        path=args.get("path"),
        title=args.get("title") or "",
        session_id=str(kw.get("session_id") or args.get("session_id") or ""),
    ),
    check_fn=check_present_files_requirements,
    emoji="📎",
    max_result_size_chars=50_000,
)
