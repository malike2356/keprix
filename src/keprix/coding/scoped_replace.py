"""Safe scoped file edit operations with rollback metadata."""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class EditOperation(str, Enum):
    REPLACE_EXACT = "replace_exact"
    REPLACE_HASHED = "replace_hashed"
    INSERT_BEFORE = "insert_before"
    INSERT_AFTER = "insert_after"
    APPEND = "append"
    CREATE = "create"


@dataclass
class EditResult:
    ok: bool
    path: str
    operation: EditOperation
    old_content_hash: str
    new_content_hash: str
    diff_preview: str
    rollback_data: dict
    error: str | None = None


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def hash_anchor(text: str, *, length: int = 8) -> str:
    """Return the short, stable hash used by hash-anchored edits.

    The short value is only a locator.  Callers must still compare the full
    anchor text before writing so a truncated-hash collision cannot mutate a
    different region.
    """
    if not 4 <= length <= 64:
        raise ValueError("anchor hash length must be between 4 and 64")
    return _hash_content(text)[:length]


def _diff_preview(old: str, new: str, path: str) -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    return "".join(difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def replace_exact_block(repo_root: Path, rel_path: str, old_block: str, new_block: str) -> EditResult:
    path = (repo_root / rel_path).resolve()
    _ensure_in_repo(path, repo_root)
    old_content = _read(path)
    if old_block not in old_content:
        return EditResult(
            ok=False,
            path=rel_path,
            operation=EditOperation.REPLACE_EXACT,
            old_content_hash=_hash_content(old_content),
            new_content_hash=_hash_content(old_content),
            diff_preview="",
            rollback_data={},
            error="Old block not found",
        )
    new_content = old_content.replace(old_block, new_block, 1)
    return _prepare_result(rel_path, EditOperation.REPLACE_EXACT, old_content, new_content, path)


def replace_hashed_block(
    repo_root: Path,
    rel_path: str,
    anchor_hash: str,
    old_block: str,
    new_block: str,
) -> EditResult:
    """Replace a block only when its content hash still matches the anchor.

    The full block is required as the collision-safe verification step.  A
    failed match never writes the file and includes a bounded surrounding
    context so an agent can re-anchor without dumping the whole file.
    """
    path = (repo_root / rel_path).resolve()
    _ensure_in_repo(path, repo_root)
    old_content = _read(path)
    operation = EditOperation.REPLACE_HASHED
    current_hash = hash_anchor(old_block, length=len(anchor_hash)) if anchor_hash else ""
    if not anchor_hash or current_hash.lower() != anchor_hash.lower() or old_block not in old_content:
        preview = _anchor_context(old_content, old_block)
        return EditResult(
            ok=False,
            path=rel_path,
            operation=operation,
            old_content_hash=_hash_content(old_content),
            new_content_hash=_hash_content(old_content),
            diff_preview="",
            rollback_data={},
            error=(
                f"Stale anchor; file changed (expected {anchor_hash or '<empty>'}, "
                f"current {current_hash or '<missing>'}). Context:\n{preview}"
            ),
        )
    new_content = old_content.replace(old_block, new_block, 1)
    return _prepare_result(rel_path, operation, old_content, new_content, path)


def insert_before(repo_root: Path, rel_path: str, marker: str, insertion: str) -> EditResult:
    path = (repo_root / rel_path).resolve()
    _ensure_in_repo(path, repo_root)
    old_content = _read(path)
    if marker not in old_content:
        return EditResult(False, rel_path, EditOperation.INSERT_BEFORE, _hash_content(old_content), _hash_content(old_content), "", {}, "Marker not found")
    new_content = old_content.replace(marker, insertion + marker, 1)
    return _prepare_result(rel_path, EditOperation.INSERT_BEFORE, old_content, new_content, path)


def insert_after(repo_root: Path, rel_path: str, marker: str, insertion: str) -> EditResult:
    path = (repo_root / rel_path).resolve()
    _ensure_in_repo(path, repo_root)
    old_content = _read(path)
    if marker not in old_content:
        return EditResult(False, rel_path, EditOperation.INSERT_AFTER, _hash_content(old_content), _hash_content(old_content), "", {}, "Marker not found")
    new_content = old_content.replace(marker, marker + insertion, 1)
    return _prepare_result(rel_path, EditOperation.INSERT_AFTER, old_content, new_content, path)


def append_to_file(repo_root: Path, rel_path: str, text: str) -> EditResult:
    path = (repo_root / rel_path).resolve()
    _ensure_in_repo(path.parent, repo_root)
    old_content = _read(path)
    new_content = old_content + text
    return _prepare_result(rel_path, EditOperation.APPEND, old_content, new_content, path)


def create_file(repo_root: Path, rel_path: str, content: str) -> EditResult:
    path = (repo_root / rel_path).resolve()
    _ensure_in_repo(path.parent, repo_root)
    if path.exists():
        return EditResult(False, rel_path, EditOperation.CREATE, "", "", "", {}, "File already exists")
    old_content = ""
    return _prepare_result(rel_path, EditOperation.CREATE, old_content, content, path)


def apply_edit(result: EditResult, repo_root: Path) -> EditResult:
    if not result.ok:
        return result
    path = (repo_root / result.path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.rollback_data["new_content"], encoding="utf-8")
    return result


def rollback_edit(result: EditResult, repo_root: Path) -> None:
    path = (repo_root / result.path).resolve()
    old_content = result.rollback_data.get("old_content", "")
    if old_content == "" and result.operation == EditOperation.CREATE and path.exists():
        path.unlink()
        return
    path.write_text(old_content, encoding="utf-8")


def _prepare_result(rel_path: str, operation: EditOperation, old_content: str, new_content: str, path: Path) -> EditResult:
    return EditResult(
        ok=True,
        path=rel_path,
        operation=operation,
        old_content_hash=_hash_content(old_content),
        new_content_hash=_hash_content(new_content),
        diff_preview=_diff_preview(old_content, new_content, rel_path),
        rollback_data={"old_content": old_content, "new_content": new_content, "path": str(path)},
    )


def _anchor_context(content: str, anchor: str, *, radius: int = 240) -> str:
    """Return bounded current text around the expected anchor location."""
    if not content:
        return "<empty file>"
    marker = anchor.splitlines()[0].strip() if anchor.splitlines() else ""
    index = content.find(marker) if marker else -1
    if index < 0:
        index = min(len(content), radius)
        start = max(0, index - radius)
    else:
        start = max(0, index - radius)
    return content[start : min(len(content), start + radius * 2)].strip()


def _ensure_in_repo(path: Path, repo_root: Path) -> None:
    root = repo_root.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes repo root: {path}") from exc
