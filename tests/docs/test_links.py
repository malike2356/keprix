"""Internal markdown links resolve to files under docs/."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
LINK_RE = re.compile(r"\]\(([^)#]+)(?:#[^)]+)?\)")


def _markdown_files() -> list[Path]:
    skip = {"site", "assets", "internal"}
    files: list[Path] = []
    for path in DOCS.rglob("*.md"):
        if path.name == "README.md":
            continue
        if any(part in skip for part in path.parts):
            continue
        files.append(path)
    return files


def _resolve_link(source: Path, target: str) -> Path | None:
    target = target.strip()
    if not target or target.startswith("http"):
        return None
    if target.startswith("/"):
        return None
    resolved = (source.parent / target).resolve()
    try:
        resolved.relative_to(DOCS.resolve())
    except ValueError:
        return None
    if resolved.suffix == "":
        for candidate in (resolved.with_suffix(".md"), resolved / "index.md"):
            if candidate.exists():
                return candidate
        return resolved.with_suffix(".md")
    return resolved


def test_no_broken_internal_doc_links() -> None:
    broken: list[str] = []
    for md_file in _markdown_files():
        content = md_file.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(content):
            target = match.group(1)
            resolved = _resolve_link(md_file, target)
            if resolved is None:
                continue
            if not resolved.exists():
                rel = md_file.relative_to(ROOT)
                broken.append(f"{rel} -> {target}")
    assert not broken, "Broken links:\n" + "\n".join(broken)
