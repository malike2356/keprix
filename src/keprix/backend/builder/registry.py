"""Project discovery and registry (Prompt 29)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from keprix.backend.builder.schemas import PROJECT_MARKERS
from keprix.backend.builder.stack_detector import detect_stack, project_tree
from keprix.backend.builder.store import get_builder_store
from keprix.backend.builder.keprix_index import KNOWN_PROJECTS


def default_scan_roots() -> list[Path]:
    raw = os.environ.get("BUILDER_ROOT", str(Path.cwd()))
    return [Path(part.strip()) for part in raw.split(":") if part.strip()]


PROJECT_SKIP_DIRS = frozenset(
    {"node_modules", "vendor", ".git", "dist", "build", ".next", "backup", "competitor-research"}
)


class ProjectRegistry:
    def __init__(self) -> None:
        self._store = get_builder_store()

    def scan(self, roots: list[Path] | None = None) -> list[dict[str, Any]]:
        discovered: dict[str, dict[str, Any]] = {}
        scan_roots = roots or default_scan_roots()

        for name, meta in KNOWN_PROJECTS.items():
            for root in scan_roots:
                candidate = (root / meta["path"]).resolve()
                if candidate.exists():
                    discovered[str(candidate)] = self._project_row(name, candidate, meta)

        for root in scan_roots:
            if not root.exists():
                continue
            for path in self._walk_project_dirs(root, max_depth=4):
                try:
                    has_marker = any((path / marker).exists() for marker in PROJECT_MARKERS)
                except PermissionError:
                    continue
                if has_marker:
                    resolved = str(path.resolve())
                    if resolved not in discovered:
                        discovered[resolved] = self._project_row(path.name, path, {})

        rows = []
        for row in discovered.values():
            rows.append(self._store.upsert_project(row))
        return rows

    def _walk_project_dirs(self, root: Path, *, max_depth: int) -> list[Path]:
        found: list[Path] = []
        stack: list[tuple[Path, int]] = [(root.resolve(), 0)]
        while stack:
            current, depth = stack.pop()
            if depth > max_depth:
                continue
            try:
                children = sorted(current.iterdir())
            except PermissionError:
                continue
            for child in children:
                if not child.is_dir() or child.name in PROJECT_SKIP_DIRS or _path_skipped(child):
                    continue
                found.append(child)
                stack.append((child, depth + 1))
        return found

    def _project_row(self, name: str, path: Path, meta: dict[str, Any]) -> dict[str, Any]:
        report = detect_stack(path)
        existing = self._store.get_project_by_path(str(path))
        status = "healthy"
        if report.estimated_completeness < 40:
            status = "wip"
        elif report.estimated_completeness < 60:
            status = "needs-update"
        return {
            "id": existing.get("id") if existing else None,
            "name": name,
            "path": str(path.resolve()),
            "tech_stack": meta.get("tech_stack") or report.languages,
            "stack_type": meta.get("stack_type") or report.stack_type,
            "framework": report.stack_type,
            "status": status,
            "keprix_app": bool(meta.get("keprix_app")),
            "governance_enrolled": bool(meta.get("governance_enrolled")),
            "meta": {"stack_report": report.to_dict()},
        }

    def list_projects(self) -> list[dict[str, Any]]:
        rows = self._store.list_projects()
        if not rows:
            rows = self.scan()
        return rows

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self._store.get_project(project_id)

    def analyse(self, project_id: str) -> dict[str, Any]:
        project = self._require_project(project_id)
        path = Path(project["path"])
        report = detect_stack(path)
        return {
            "project": project,
            "stack_report": report.to_dict(),
            "tree_sample": project_tree(path, depth=2)[:100],
        }

    def tree(self, project_id: str, depth: int = 2) -> list[dict[str, str]]:
        project = self._require_project(project_id)
        return project_tree(Path(project["path"]), depth=depth)

    def _require_project(self, project_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        if project is None:
            raise ValueError("Project not found")
        return project


_registry: ProjectRegistry | None = None


def _path_skipped(path: Path) -> bool:
    return any(part in PROJECT_SKIP_DIRS for part in path.parts)


def get_project_registry() -> ProjectRegistry:
    global _registry
    if _registry is None:
        _registry = ProjectRegistry()
    return _registry
