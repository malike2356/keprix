"""Codebase self-indexing for Keprix RAG."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from pathlib import Path

from keprix.memory.rag.indexer import RagIndexer

CODEBASE_SOURCE_TYPE = "codebase"
DEFAULT_INCLUDE_ROOTS = (
    "src/keprix",
    "frontend/src",
    "tests",
    "docs",
    "config",
    "pyproject.toml",
    "README.md",
    "AGENTS.md",
)
DEFAULT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".sql",
    ".css",
    ".scss",
}
SKIP_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "node_modules",
    "coverage",
    "graphify-out",
    "1st-plan",
}
SECRET_NAME_PARTS = (
    ".env",
    "secret",
    "credential",
    "credentials",
    "private",
    "token",
    "stripe-credentials",
)


@dataclass(frozen=True)
class CodebaseIndexStats:
    files_seen: int = 0
    files_indexed: int = 0
    files_skipped: int = 0
    chunks: int = 0
    bytes_indexed: int = 0
    root: str = ""

    def to_dict(self) -> dict[str, int | str]:
        return {
            "files_seen": self.files_seen,
            "files_indexed": self.files_indexed,
            "files_skipped": self.files_skipped,
            "chunks": self.chunks,
            "bytes_indexed": self.bytes_indexed,
            "root": self.root,
        }


def default_codebase_root() -> Path:
    configured = os.getenv("KEPRIX_CODEBASE_ROOT") or os.getenv("KEPRIX_REPO_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    try:
        from keprix.api.codebase_context import resolve_repo_root

        detected = resolve_repo_root()
        if detected is not None:
            return detected
    except Exception:
        pass
    return Path.cwd().resolve()


def _is_secret_path(path: Path) -> bool:
    lowered_parts = [part.lower() for part in path.parts]
    lowered_name = path.name.lower()
    return any(part in lowered_name for part in SECRET_NAME_PARTS) or any(
        part in SECRET_NAME_PARTS for part in lowered_parts
    )


def _safe_relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _iter_roots(root: Path, include_roots: list[str] | None) -> list[Path]:
    roots = include_roots or list(DEFAULT_INCLUDE_ROOTS)
    resolved: list[Path] = []
    for item in roots:
        candidate = (root / item).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.exists():
            resolved.append(candidate)
    return resolved


def discover_codebase_files(
    *,
    root: Path | None = None,
    include_roots: list[str] | None = None,
    extensions: set[str] | None = None,
    max_files: int = 2000,
    max_file_bytes: int = 250_000,
) -> list[Path]:
    base = (root or default_codebase_root()).resolve()
    allowed_extensions = extensions or DEFAULT_EXTENSIONS
    files: list[Path] = []
    seen: set[Path] = set()
    for start in _iter_roots(base, include_roots):
        candidates = [start] if start.is_file() else start.rglob("*")
        for path in candidates:
            resolved = path.resolve()
            if resolved in seen or not resolved.is_file():
                continue
            seen.add(resolved)
            try:
                relative_parts = resolved.relative_to(base).parts
            except ValueError:
                continue
            if any(part in SKIP_DIRS for part in relative_parts):
                continue
            if _is_secret_path(resolved):
                continue
            if resolved.suffix.lower() not in allowed_extensions:
                continue
            try:
                if resolved.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            files.append(resolved)
            if len(files) >= max_files:
                return sorted(files)
    return sorted(files)


def _python_summary(text: str) -> tuple[list[str], list[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], []

    symbols: list[str] = []
    imports: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            symbols.append(node.name)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names[:5])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return symbols[:40], imports[:40]


def _text_summary(text: str, extension: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    symbols: list[str] = []
    imports: list[str] = []
    if extension in {".ts", ".tsx", ".js", ".jsx"}:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("export function ", "function ", "export class ", "class ")):
                symbols.append(stripped[:120])
            if stripped.startswith(("import ", "export {")):
                imports.append(stripped[:120])
    elif extension == ".md":
        symbols = [line.strip("# ").strip() for line in lines if line.startswith("#")][:30]
    return symbols[:40], imports[:40]


def build_codebase_document(path: Path, root: Path | None = None) -> tuple[str, str]:
    base = (root or default_codebase_root()).resolve()
    relative = _safe_relative(path, base)
    raw = path.read_text(encoding="utf-8", errors="ignore")
    extension = path.suffix.lower()
    if extension == ".py":
        symbols, imports = _python_summary(raw)
    else:
        symbols, imports = _text_summary(raw, extension)

    lines = raw.splitlines()
    excerpt = "\n".join(lines[:420])
    parts = [
        f"Keprix codebase file: {relative}",
        f"Extension: {extension or 'none'}",
        f"Line count: {len(lines)}",
    ]
    if symbols:
        parts.append("Symbols/headings: " + ", ".join(symbols))
    if imports:
        parts.append("Imports: " + ", ".join(imports))
    parts.append("Content excerpt:")
    parts.append(excerpt)
    return relative, "\n".join(parts).strip()


class CodebaseRagIndexer:
    def __init__(self, rag_indexer: RagIndexer, *, root: Path | None = None) -> None:
        self.rag_indexer = rag_indexer
        self.root = (root or default_codebase_root()).resolve()

    async def index(
        self,
        *,
        user_id: str,
        include_roots: list[str] | None = None,
        max_files: int = 2000,
        max_file_bytes: int = 250_000,
    ) -> CodebaseIndexStats:
        files = discover_codebase_files(
            root=self.root,
            include_roots=include_roots,
            max_files=max_files,
            max_file_bytes=max_file_bytes,
        )
        chunks = 0
        indexed = 0
        bytes_indexed = 0
        for path in files:
            try:
                source_id, document = build_codebase_document(path, self.root)
                bytes_indexed += path.stat().st_size
                chunks += await self.rag_indexer.ingest(
                    user_id=user_id,
                    source_type=CODEBASE_SOURCE_TYPE,
                    source_id=source_id,
                    content=document,
                )
                indexed += 1
            except (OSError, UnicodeError):
                continue
        return CodebaseIndexStats(
            files_seen=len(files),
            files_indexed=indexed,
            files_skipped=max(0, len(files) - indexed),
            chunks=chunks,
            bytes_indexed=bytes_indexed,
            root=str(self.root),
        )
