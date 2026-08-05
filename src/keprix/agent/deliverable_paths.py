"""Computer-use deliverable path contract (Prompt 293).

Scratch for intermediate work, uploads for user files (read-mostly),
outputs for user-visible finals. ``present_files`` only accepts outputs.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Sequence


class DeliverableZone(str, Enum):
    SCRATCH = "scratch"
    UPLOADS = "uploads"
    OUTPUTS = "outputs"
    WORKSPACE = "workspace"
    SKILL = "skill"
    UNKNOWN = "unknown"


class DeliverableIntent(str, Enum):
    INLINE = "inline"
    FILE = "file"


@dataclass(frozen=True)
class DeliverableLayout:
    """Session-scoped deliverable directories."""

    scratch_dir: Path
    uploads_dir: Path
    outputs_dir: Path
    root_dir: Path
    session_id: str
    cwd: Path

    def ensure(self) -> DeliverableLayout:
        for path in (self.root_dir, self.scratch_dir, self.uploads_dir, self.outputs_dir):
            path.mkdir(parents=True, exist_ok=True)
        return self

    def zone_for(self, path: Path | str) -> DeliverableZone:
        try:
            resolved = Path(path).expanduser().resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            return DeliverableZone.UNKNOWN

        if _is_under(resolved, self.outputs_dir):
            return DeliverableZone.OUTPUTS
        if _is_under(resolved, self.scratch_dir):
            return DeliverableZone.SCRATCH
        if _is_under(resolved, self.uploads_dir):
            return DeliverableZone.UPLOADS
        if _looks_like_skill_root(resolved):
            return DeliverableZone.SKILL
        if _is_under(resolved, self.cwd):
            return DeliverableZone.WORKSPACE
        return DeliverableZone.UNKNOWN

    @property
    def presented_index_path(self) -> Path:
        return self.root_dir / "presented.json"


def resolve_deliverable_layout(
    session_id: str | None = None,
    *,
    cwd: Path | str | None = None,
    create: bool = True,
) -> DeliverableLayout:
    """Resolve the three-directory layout for a session."""
    sid = _normalize_session_id(session_id or os.getenv("KEPRIX_SESSION_ID") or "default")
    base_cwd = Path(cwd) if cwd is not None else _resolve_cwd()
    root = base_cwd / ".keprix" / "deliverables" / sid
    layout = DeliverableLayout(
        scratch_dir=root / "scratch",
        uploads_dir=root / "uploads",
        outputs_dir=root / "outputs",
        root_dir=root,
        session_id=sid,
        cwd=base_cwd.resolve(strict=False),
    )
    if create:
        layout.ensure()
    return layout


def layout_for_path(path: Path | str) -> DeliverableLayout | None:
    """If path sits under ``.keprix/deliverables/<session>/...``, return that layout."""
    try:
        resolved = Path(path).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return None
    for zone_dir in (resolved, *resolved.parents):
        if zone_dir.name not in {"scratch", "uploads", "outputs"}:
            continue
        session_root = zone_dir.parent
        deliverables = session_root.parent
        keprix = deliverables.parent
        if deliverables.name != "deliverables" or keprix.name != ".keprix":
            continue
        cwd = keprix.parent
        return resolve_deliverable_layout(session_root.name, cwd=cwd, create=False)
    return None


def classify_deliverable_intent(user_text: str) -> DeliverableIntent:
    """Heuristic: standalone artifacts -> file; strategy/brainstorm -> inline."""
    text = (user_text or "").strip().lower()
    if not text:
        return DeliverableIntent.INLINE

    save_markers = (
        "save as",
        "save to",
        "write a file",
        "create a file",
        "export",
        "download",
        "as a pdf",
        "as pdf",
        "as a docx",
        "as docx",
        "as a pptx",
        "powerpoint",
        "spreadsheet",
        "csv file",
    )
    if any(marker in text for marker in save_markers):
        return DeliverableIntent.FILE

    file_artifacts = (
        "blog post",
        "blog article",
        "write a report",
        "write an report",
        "write a document",
        "create a presentation",
        "build a component",
        "react component",
        "landing page",
        "slide deck",
        "whitepaper",
        "proposal document",
    )
    if any(marker in text for marker in file_artifacts):
        return DeliverableIntent.FILE

    inline_markers = (
        "brainstorm",
        "strategy",
        "summarize",
        "summary",
        "what do you think",
        "quick thoughts",
        "outline briefly",
        "in chat",
        "just tell me",
    )
    if any(marker in text for marker in inline_markers):
        return DeliverableIntent.INLINE

    # Default: short Q&A stays inline.
    if len(text.split()) < 12 and "?" in text:
        return DeliverableIntent.INLINE
    return DeliverableIntent.INLINE


def is_presentable(path: Path | str, layout: DeliverableLayout | None = None) -> bool:
    layout = layout or resolve_deliverable_layout(create=False)
    try:
        resolved = Path(path).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return False
    if not resolved.is_file():
        return False
    return layout.zone_for(resolved) == DeliverableZone.OUTPUTS


def copy_to_outputs(
    source: Path | str,
    *,
    layout: DeliverableLayout | None = None,
    dest_name: str | None = None,
) -> Path:
    """Copy a scratch/workspace file into outputs (never from skill roots in-place)."""
    layout = layout or resolve_deliverable_layout()
    layout.ensure()
    src = Path(source).expanduser().resolve(strict=False)
    if not src.is_file():
        raise FileNotFoundError(f"source file not found: {src}")
    zone = layout.zone_for(src)
    if zone == DeliverableZone.SKILL:
        # Allowed: copy-out from skill roots into outputs.
        pass
    if zone == DeliverableZone.UPLOADS:
        # Prefer staging via scratch first for edits; copy to outputs is OK for present.
        pass
    name = dest_name or src.name
    dest = (layout.outputs_dir / name).resolve(strict=False)
    if not _is_under(dest, layout.outputs_dir):
        raise ValueError("destination escapes outputs_dir")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def stage_upload_to_scratch(
    upload_path: Path | str,
    *,
    layout: DeliverableLayout | None = None,
    dest_name: str | None = None,
) -> Path:
    """Copy a user upload into scratch before editing (never overwrite uploads)."""
    layout = layout or resolve_deliverable_layout()
    layout.ensure()
    src = Path(upload_path).expanduser().resolve(strict=False)
    if not src.is_file():
        raise FileNotFoundError(f"upload not found: {src}")
    name = dest_name or src.name
    dest = (layout.scratch_dir / name).resolve(strict=False)
    if not _is_under(dest, layout.scratch_dir):
        raise ValueError("destination escapes scratch_dir")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def register_presented_files(
    paths: Sequence[Path | str],
    *,
    layout: DeliverableLayout | None = None,
    title: str = "",
) -> list[dict[str, Any]]:
    """Record presented outputs on the session index."""
    layout = layout or resolve_deliverable_layout()
    layout.ensure()
    index = _load_presented_index(layout)
    now = time.time()
    recorded: list[dict[str, Any]] = []
    for raw in paths:
        path = Path(raw).expanduser().resolve(strict=False)
        entry = {
            "path": str(path),
            "name": path.name,
            "title": title or path.name,
            "presented_at": now,
            "size": path.stat().st_size if path.is_file() else 0,
        }
        # De-dupe by path, keep latest.
        index["files"] = [f for f in index.get("files", []) if f.get("path") != entry["path"]]
        index["files"].append(entry)
        recorded.append(entry)
    index["updated_at"] = now
    _save_presented_index(layout, index)
    return recorded


def list_presented_files(layout: DeliverableLayout | None = None) -> list[dict[str, Any]]:
    layout = layout or resolve_deliverable_layout(create=False)
    if not layout.presented_index_path.is_file():
        return []
    return list(_load_presented_index(layout).get("files") or [])


def annotate_write_zone(
    resolved_path: str | Path,
    *,
    layout: DeliverableLayout | None = None,
) -> dict[str, Any]:
    """Return metadata for write_file / patch results."""
    layout = layout or resolve_deliverable_layout(create=False)
    zone = layout.zone_for(resolved_path)
    meta: dict[str, Any] = {
        "deliverable_zone": zone.value,
        "scratch_dir": str(layout.scratch_dir),
        "outputs_dir": str(layout.outputs_dir),
        "uploads_dir": str(layout.uploads_dir),
    }
    if zone == DeliverableZone.SCRATCH:
        meta["hint"] = (
            "Scratch file is not user-visible. Copy to outputs and call "
            "present_files when ready."
        )
    elif zone == DeliverableZone.OUTPUTS:
        meta["hint"] = "Final deliverable path. Call present_files so the user can open it."
    elif zone == DeliverableZone.UPLOADS:
        meta["hint"] = (
            "Uploads are read-mostly. Copy to scratch before editing; "
            "never overwrite uploads in place."
        )
    elif zone == DeliverableZone.SKILL:
        meta["hint"] = "Skill roots are read-only. Copy out to scratch/outputs to edit."
    return meta


def guard_upload_overwrite(
    resolved_path: str | Path,
    *,
    layout: DeliverableLayout | None = None,
) -> str | None:
    """Return an error message if a write would overwrite an upload in place."""
    layout = layout or resolve_deliverable_layout(create=False)
    path = Path(resolved_path).expanduser().resolve(strict=False)
    if layout.zone_for(path) != DeliverableZone.UPLOADS:
        return None
    if path.is_file():
        return (
            "Refusing to overwrite user upload in place. "
            f"Copy to scratch first (e.g. {layout.scratch_dir / path.name}), "
            "edit there, then copy finals to outputs and call present_files."
        )
    return None


def guard_skill_write(
    resolved_path: str | Path,
    *,
    layout: DeliverableLayout | None = None,
) -> str | None:
    """Return an error if writing into a skill root."""
    layout = layout or resolve_deliverable_layout(create=False)
    path = Path(resolved_path).expanduser().resolve(strict=False)
    if layout.zone_for(path) == DeliverableZone.SKILL:
        return (
            "Skill roots are read-only. Copy the file to scratch or outputs "
            f"(e.g. {layout.scratch_dir / path.name}) before editing."
        )
    return None


def short_vs_long_strategy(line_count: int) -> str:
    """Fable short vs long file creation strategy label."""
    if line_count < 100:
        return "short"
    return "long"


def layout_prompt_block(layout: DeliverableLayout | None = None) -> str:
    layout = layout or resolve_deliverable_layout()
    return (
        "Deliverable paths:\n"
        f"- scratch (agent-only): {layout.scratch_dir}\n"
        f"- uploads (read-mostly): {layout.uploads_dir}\n"
        f"- outputs (user-visible finals): {layout.outputs_dir}\n"
        "Short files (<100 lines): write once to outputs, then present_files.\n"
        "Long files: iterate in scratch, copy final to outputs, then present_files.\n"
        "Prefer markdown over docx unless the user asks for Word.\n"
        "Never present scratch paths; copy to outputs first."
    )


def _normalize_session_id(session_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (session_id or "default").strip())
    return cleaned[:120] or "default"


def _resolve_cwd() -> Path:
    try:
        from agent.runtime_cwd import resolve_agent_cwd

        return resolve_agent_cwd()
    except Exception:
        return Path(os.getcwd())


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except (ValueError, OSError, RuntimeError):
        return False


def _looks_like_skill_root(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    markers = {"skills", "optional-skills", "skill.md"}
    if "skill.md" in path.name.lower():
        return True
    # Path contains a skills directory segment and is under a known home.
    if "skills" in parts or "optional-skills" in parts:
        return True
    try:
        from keprix_constants import get_skills_dir, get_optional_skills_dir

        for root in (get_skills_dir(), get_optional_skills_dir()):
            if root and _is_under(path, Path(root)):
                return True
    except Exception:
        pass
    return False


def _load_presented_index(layout: DeliverableLayout) -> dict[str, Any]:
    path = layout.presented_index_path
    if not path.is_file():
        return {"files": [], "session_id": layout.session_id}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"files": [], "session_id": layout.session_id}
    if not isinstance(data, dict):
        return {"files": [], "session_id": layout.session_id}
    data.setdefault("files", [])
    data.setdefault("session_id", layout.session_id)
    return data


def _save_presented_index(layout: DeliverableLayout, data: dict[str, Any]) -> None:
    layout.presented_index_path.parent.mkdir(parents=True, exist_ok=True)
    layout.presented_index_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
