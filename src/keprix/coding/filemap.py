"""Repository file map builder."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RepoFilemap:
    root: str
    packages: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    routes: list[str] = field(default_factory=list)
    configs: list[str] = field(default_factory=list)
    recently_changed: list[str] = field(default_factory=list)
    symbols: dict[str, list[str]] = field(default_factory=dict)


def _rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def build_filemap(repo_path: Path, *, max_files: int = 500) -> RepoFilemap:
    root = repo_path.resolve()
    if not root.is_dir():
        raise ValueError(f"Repo path does not exist: {repo_path}")

    packages: list[str] = []
    entry_points: list[str] = []
    tests: list[str] = []
    routes: list[str] = []
    configs: list[str] = []
    symbols: dict[str, list[str]] = {}
    count = 0

    for path in sorted(root.rglob("*")):
        if count >= max_files:
            break
        if not path.is_file():
            continue
        if any(part in {".git", "node_modules", ".venv", "vendor", "__pycache__"} for part in path.parts):
            continue
        rel = _rel(path, root)
        count += 1
        lower = rel.lower()
        if lower.endswith(("pyproject.toml", "package.json", "composer.json", "setup.py", "go.mod")):
            packages.append(rel)
        if lower.endswith(("main.py", "__main__.py", "index.ts", "index.js", "app.py", "server.py")):
            entry_points.append(rel)
        if "/test" in lower or lower.startswith("test") or "/tests/" in lower or lower.endswith("_test.py"):
            tests.append(rel)
        if "route" in lower or "/api/" in lower:
            routes.append(rel)
        if lower.endswith((".yaml", ".yml", ".env.example", ".toml", ".ini", "config.py")):
            configs.append(rel)
        if path.suffix == ".py" and path.stat().st_size < 200_000:
            symbols[rel] = _extract_python_symbols(path)

    recently_changed = _git_changed_files(root)
    return RepoFilemap(
        root=str(root),
        packages=packages[:50],
        entry_points=entry_points[:50],
        tests=tests[:100],
        routes=routes[:100],
        configs=configs[:50],
        recently_changed=recently_changed[:50],
        symbols=symbols,
    )


def _git_changed_files(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "log", "-n", "5", "--name-only", "--pretty=format:"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if proc.returncode != 0:
            return []
        seen: set[str] = set()
        ordered: list[str] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                ordered.append(line)
        return ordered
    except Exception:
        return []


def _extract_python_symbols(path: Path) -> list[str]:
    symbols: list[str] = []
    try:
        import ast

        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbols.append(f"def {node.name}")
            elif isinstance(node, ast.ClassDef):
                symbols.append(f"class {node.name}")
    except Exception:
        return symbols
    return symbols[:40]
