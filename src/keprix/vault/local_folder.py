"""Local folder markdown vault provider."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from keprix.research_workspace.obsidian.frontmatter import dump_frontmatter, parse_frontmatter
from keprix.vault.provider import VaultFile, VaultProvider

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
EXCLUDED_PARTS = {".git", ".trash", ".obsidian", ".keprix", "logseq"}


class LocalFolderVault(VaultProvider):
    def __init__(self, root_path: str | Path) -> None:
        self.root = Path(root_path).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    async def list_files(self, path: str = "/") -> list[VaultFile]:
        folder = self._resolve(path)
        if not folder.is_dir():
            raise FileNotFoundError(path)
        rows: list[VaultFile] = []
        for item in sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if self._skip(item, root=self.root):
                continue
            stat = item.stat()
            rows.append(
                VaultFile(
                    path=item.relative_to(self.root).as_posix(),
                    name=item.name,
                    is_dir=item.is_dir(),
                    size=0 if item.is_dir() else stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                )
            )
        return rows

    async def read_file(self, path: str) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise FileNotFoundError(path)
        return target.read_text(encoding="utf-8")

    async def write_file(self, path: str, content: str) -> None:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            existing_meta, _existing_body = parse_frontmatter(target.read_text(encoding="utf-8"))
            incoming_meta, incoming_body = parse_frontmatter(content)
            if existing_meta and not incoming_meta:
                content = dump_frontmatter(existing_meta, content)
            elif existing_meta and incoming_meta:
                content = dump_frontmatter({**existing_meta, **incoming_meta}, incoming_body)
        target.write_text(content, encoding="utf-8")

    async def delete_file(self, path: str) -> None:
        target = self._resolve(path)
        if not target.is_file():
            raise FileNotFoundError(path)
        target.unlink()

    async def search(self, query: str) -> list[VaultFile]:
        needle = query.lower().strip()
        if not needle:
            return []
        matches: list[VaultFile] = []
        for path in self._markdown_files():
            text = path.read_text(encoding="utf-8", errors="ignore")
            links = " ".join(_extract_wikilinks(text))
            haystack = f"{path.stem} {path.name} {links} {text}".lower()
            if needle in haystack:
                stat = path.stat()
                matches.append(
                    VaultFile(
                        path=path.relative_to(self.root).as_posix(),
                        name=path.name,
                        size=stat.st_size,
                        modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    )
                )
        return matches

    async def get_backlinks(self, path: str) -> list[str]:
        target = self._resolve(path)
        stem = target.stem
        backlinks: list[str] = []
        for candidate in self._markdown_files():
            if candidate == target:
                continue
            links = _extract_wikilinks(candidate.read_text(encoding="utf-8", errors="ignore"))
            if stem in {Path(link).stem for link in links}:
                backlinks.append(candidate.relative_to(self.root).as_posix())
        return sorted(backlinks)

    async def get_graph(self) -> dict[str, list[dict[str, str]]]:
        files = self._markdown_files()
        by_stem = {path.stem: path.relative_to(self.root).as_posix() for path in files}
        nodes = [{"id": path.relative_to(self.root).as_posix(), "label": path.stem} for path in files]
        edges: list[dict[str, str]] = []
        for path in files:
            source = path.relative_to(self.root).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            for link in _extract_wikilinks(text):
                target = by_stem.get(Path(link).stem)
                if target:
                    edges.append({"source": source, "target": target})
        return {"nodes": nodes, "edges": edges}

    def _markdown_files(self) -> list[Path]:
        return sorted(path for path in self.root.rglob("*.md") if not self._skip(path, root=self.root))

    def _resolve(self, path: str | Path) -> Path:
        raw = str(path or "/").lstrip("/")
        target = (self.root / raw).resolve()
        if target != self.root and self.root not in target.parents:
            raise ValueError("vault path must stay inside root")
        return target

    @staticmethod
    def _skip(path: Path, *, root: Path | None = None) -> bool:
        parts = path.parts
        if root is not None:
            try:
                parts = path.relative_to(root).parts
            except ValueError:
                parts = path.parts
        return any(part in EXCLUDED_PARTS for part in parts)


def _extract_wikilinks(text: str) -> list[str]:
    _meta, body = parse_frontmatter(text)
    return [match.strip() for match in WIKILINK_RE.findall(body) if match.strip()]
