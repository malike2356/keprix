"""Patch formatting and application from edit results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from keprix.coding.scoped_replace import EditResult, apply_edit, rollback_edit


@dataclass
class PatchBundle:
    patch_text: str
    edits: list[EditResult] = field(default_factory=list)
    explanation: str = ""


def format_patch(edits: list[EditResult]) -> str:
    parts: list[str] = ["*** Begin Patch"]
    for edit in edits:
        if not edit.ok:
            continue
        if edit.operation.value == "create":
            parts.append(f"*** Add File: {edit.path}")
            for line in edit.rollback_data["new_content"].splitlines():
                parts.append(f"+{line}")
        else:
            parts.append(f"*** Update File: {edit.path}")
            for line in edit.diff_preview.splitlines():
                if line.startswith(("+", "-", " ")) and not line.startswith(("+++", "---", "@@")):
                    parts.append(line)
    parts.append("*** End Patch")
    return "\n".join(parts)


def apply_patch_bundle(repo_root: Path, bundle: PatchBundle) -> list[EditResult]:
    applied: list[EditResult] = []
    for edit in bundle.edits:
        if not edit.ok:
            continue
        applied.append(apply_edit(edit, repo_root))
    return applied


def rollback_patch(repo_root: Path, edits: list[EditResult]) -> None:
    for edit in reversed(edits):
        if edit.ok:
            rollback_edit(edit, repo_root)
