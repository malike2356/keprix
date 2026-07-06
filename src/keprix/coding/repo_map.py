"""Aider-style compact repository map with gitignore and blame metadata."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from keprix.coding.filemap import build_filemap

_IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "vendor",
    "__pycache__",
    "dist",
    "build",
    ".next",
    "coverage",
}
_SECRET_PATTERNS = (
    ".env",
    ".pem",
    ".key",
    "id_rsa",
    "credentials",
    "secrets",
    ".access.config",
)
_SECRET_NAME_RE = re.compile(r"(?i)(secret|password|credential|api[_-]?key|token)")


@dataclass
class BlameLine:
    line_no: int
    author: str
    summary: str


@dataclass
class RepoMapEntry:
    path: str
    symbols: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    blame: list[BlameLine] = field(default_factory=list)


@dataclass
class RepoMap:
    root: str
    files: list[str] = field(default_factory=list)
    entries: dict[str, RepoMapEntry] = field(default_factory=dict)
    routes: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    recently_changed: list[str] = field(default_factory=list)
    ignored_count: int = 0

    def compact_text(self, *, max_files: int = 40) -> str:
        lines = [f"Repo: {self.root}"]
        if self.recently_changed:
            lines.append("Recent: " + ", ".join(self.recently_changed[:8]))
        lines.append("Files:")
        for path in self.files[:max_files]:
            entry = self.entries.get(path)
            symbol_text = ""
            if entry and entry.symbols:
                symbol_text = " | " + ", ".join(entry.symbols[:6])
            lines.append(f"  {path}{symbol_text}")
        if self.tests:
            lines.append("Tests: " + ", ".join(self.tests[:10]))
        if self.routes:
            lines.append("Routes: " + ", ".join(self.routes[:10]))
        return "\n".join(lines)


def build_repo_map(repo_path: Path, *, max_files: int = 300, allowed_paths: list[str] | None = None) -> RepoMap:
    root = repo_path.resolve()
    if not root.is_dir():
        raise ValueError(f"Repo path does not exist: {repo_path}")

    ignore_rules = _load_gitignore(root)
    filemap = build_filemap(root, max_files=max_files)
    files: list[str] = []
    entries: dict[str, RepoMapEntry] = {}
    ignored = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if len(files) >= max_files:
            break
        rel = str(path.relative_to(root)).replace("\\", "/")
        if allowed_paths is not None:
            if not any(rel.startswith(prefix) for prefix in allowed_paths):
                ignored += 1
                continue
        if _should_ignore(rel, ignore_rules):
            ignored += 1
            continue
        if _is_secret_path(rel):
            ignored += 1
            continue
        files.append(rel)
        entries[rel] = RepoMapEntry(
            path=rel,
            symbols=filemap.symbols.get(rel, _scan_symbols(path)),
            imports=_scan_imports(path),
            blame=_git_blame_summary(root, rel),
        )

    return RepoMap(
        root=str(root),
        files=files,
        entries=entries,
        routes=filemap.routes,
        tests=filemap.tests,
        recently_changed=filemap.recently_changed,
        ignored_count=ignored,
    )


def _load_gitignore(root: Path) -> list[str]:
    rules: list[str] = []
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return rules
    for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            rules.append(line)
    return rules


def _should_ignore(rel: str, rules: list[str]) -> bool:
    parts = Path(rel).parts
    if any(part in _IGNORED_DIRS for part in parts):
        return True
    for rule in rules:
        cleaned = rule.rstrip("/")
        if cleaned.startswith("/"):
            if fnmatch(rel, cleaned.lstrip("/")) or rel.startswith(cleaned.lstrip("/") + "/"):
                return True
        elif "/" in cleaned:
            if fnmatch(rel, cleaned) or rel.startswith(cleaned + "/"):
                return True
        else:
            if fnmatch(rel, cleaned) or any(fnmatch(part, cleaned) for part in parts):
                return True
    return False


def _is_secret_path(rel: str) -> bool:
    lower = rel.lower()
    if any(token in lower for token in _SECRET_PATTERNS):
        return True
    name = Path(rel).name
    return bool(_SECRET_NAME_RE.search(name))


def _scan_symbols(path: Path) -> list[str]:
    if path.suffix != ".py":
        return []
    try:
        import ast

        tree = ast.parse(path.read_text(encoding="utf-8"))
        symbols: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbols.append(f"def {node.name}")
            elif isinstance(node, ast.ClassDef):
                symbols.append(f"class {node.name}")
        return symbols[:40]
    except Exception:
        return []


def _scan_imports(path: Path) -> list[str]:
    imports: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return imports
    if path.suffix == ".py":
        try:
            import ast

            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
        except Exception:
            pass
    else:
        for match in re.finditer(r'(?:import|from)\s+["\']([^"\']+)["\']', text):
            imports.append(match.group(1))
    return sorted(set(imports))[:30]


def _git_blame_summary(root: Path, rel: str, *, max_lines: int = 3) -> list[BlameLine]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "blame", "-l", "-L", f"1,{max_lines}", rel],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if proc.returncode != 0:
            return []
        blame: list[BlameLine] = []
        for index, line in enumerate(proc.stdout.splitlines(), start=1):
            author = "unknown"
            summary = line.strip()[:120]
            match = re.match(r"^[^(]+\(([^)]+)\)", line)
            if match:
                author = match.group(1).strip()
            blame.append(BlameLine(line_no=index, author=author, summary=summary))
        return blame
    except Exception:
        return []
