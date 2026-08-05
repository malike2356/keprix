"""Deterministic markdown indexes for structured workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


IGNORED_NAMES = {"index.md", "KEPRIX.md", ".DS_Store"}


@dataclass
class IndexedFile:
    path: Path
    topic: str
    status: str
    date: str


def _topic_from_name(path: Path) -> str:
    stem = path.stem.replace("-", " ").replace("_", " ").strip()
    return stem.title() or path.name


def _status_for(path: Path) -> str:
    text = path.name.lower()
    if "draft" in text:
        return "Draft"
    if "done" in text or "delivered" in text or "processed" in text:
        return "Processed"
    return "Pending"


class WorkspaceIndexer:
    def __init__(self, workspace_path: str | Path) -> None:
        self.root = Path(workspace_path)

    def scan_folder(self, folder: str | Path = ".") -> list[IndexedFile]:
        folder_path = self._folder_path(folder)
        if not folder_path.exists():
            return []
        files: list[IndexedFile] = []
        for path in sorted(item for item in folder_path.iterdir() if item.is_file() and item.name not in IGNORED_NAMES):
            stat = path.stat()
            files.append(
                IndexedFile(
                    path=path,
                    topic=_topic_from_name(path),
                    status=_status_for(path),
                    date=datetime.fromtimestamp(stat.st_mtime, timezone.utc).date().isoformat(),
                )
            )
        return files

    def render_index(self, folder: str | Path = ".") -> str:
        folder_path = self._folder_path(folder)
        display = "/" if folder_path == self.root else f"/{folder_path.relative_to(self.root).as_posix()}"
        files = self.scan_folder(folder)
        updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        processed = sum(1 for item in files if item.status == "Processed")
        lines = [
            f"# {display} -- Index",
            "",
            f"Last updated: {updated}",
            f"Total files: {len(files)} ({processed} processed, {len(files) - processed} pending)",
            "",
            "## Files",
            "",
            "| File | Topic | Date Added | Status |",
            "| --- | --- | --- | --- |",
        ]
        for item in files:
            rel = item.path.relative_to(folder_path).as_posix()
            lines.append(f"| [{rel}]({rel}) | {item.topic} | {item.date} | {item.status} |")
        lines.extend(["", "## Topics covered", ""])
        if files:
            for item in files:
                lines.append(f"- {item.topic}: `{item.path.name}`")
        else:
            lines.append("- No files yet.")
        lines.append("")
        return "\n".join(lines)

    def update_index(self, folder: str | Path = ".") -> str:
        folder_path = self._folder_path(folder)
        folder_path.mkdir(parents=True, exist_ok=True)
        content = self.render_index(folder)
        (folder_path / "index.md").write_text(content, encoding="utf-8")
        return content

    def reindex_all(self) -> list[Path]:
        updated: list[Path] = []
        folders = [self.root] + [item for item in sorted(self.root.rglob("*")) if item.is_dir()]
        for folder in folders:
            self.update_index(folder.relative_to(self.root) if folder != self.root else ".")
            updated.append(folder / "index.md")
        return updated

    def on_file_change(self, path: str | Path, action: str = "changed") -> str:
        _ = action
        target = Path(path)
        folder = target.parent if target.is_absolute() else (self.root / target).parent
        return self.update_index(folder.relative_to(self.root))

    def _folder_path(self, folder: str | Path) -> Path:
        candidate = Path(folder)
        if candidate.is_absolute():
            folder_path = candidate
        elif str(candidate) == ".":
            folder_path = self.root
        else:
            folder_path = self.root / candidate
        resolved_root = self.root.resolve()
        resolved_folder = folder_path.resolve()
        if resolved_folder != resolved_root and resolved_root not in resolved_folder.parents:
            raise ValueError("folder must stay within workspace")
        return folder_path
