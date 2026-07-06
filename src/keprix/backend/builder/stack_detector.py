"""Detect project tech stack from filesystem (Prompt 29)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from keprix.backend.builder.schemas import StackReport


def detect_stack(project_path: Path) -> StackReport:
    root = project_path.resolve()
    languages: set[str] = set()
    dependencies: dict[str, str] = {}
    entry_points: list[str] = []
    database = "none"
    stack_type = "unknown"

    if (root / "wp-config.php").exists():
        stack_type = "wordpress"
        languages.add("php")
        entry_points.append("wp-config.php")
    elif (root / "artisan").exists() and (root / "composer.json").exists():
        stack_type = "laravel"
        languages.add("php")
        entry_points.append("artisan")
    elif (root / "composer.json").exists():
        stack_type = "custom-php"
        languages.add("php")
        entry_points.append("index.php")
    elif (root / "package.json").exists():
        pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        dependencies.update({key: str(value) for key, value in list(deps.items())[:20]})
        if deps.get("next"):
            stack_type = "nextjs"
        elif deps.get("nuxt") or deps.get("nuxt3"):
            stack_type = "nuxt"
        elif deps.get("@tauri-apps/api"):
            stack_type = "tauri"
        elif deps.get("electron"):
            stack_type = "electron"
        elif deps.get("react-native") or deps.get("expo"):
            stack_type = "react-native"
        elif deps.get("react"):
            stack_type = "react-spa" if (root / "vite.config.ts").exists() or (root / "vite.config.js").exists() else "node-express"
        else:
            stack_type = "node-express"
        languages.add("javascript")
        if (root / "tsconfig.json").exists():
            languages.add("typescript")
        for candidate in ("src/app/page.tsx", "src/main.tsx", "index.js", "server.js", "app/page.tsx"):
            if (root / candidate).exists():
                entry_points.append(candidate)
    elif (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        languages.add("python")
        text = ""
        if (root / "pyproject.toml").exists():
            text = (root / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
        if "fastapi" in text.lower():
            stack_type = "python-fastapi"
        elif "flask" in text.lower():
            stack_type = "python-flask"
        else:
            stack_type = "python-cli"
        for candidate in ("main.py", "app/main.py", "src/main.py"):
            if (root / candidate).exists():
                entry_points.append(candidate)
    elif (root / "build.gradle.kts").exists() or (root / "build.gradle").exists():
        stack_type = "kotlin"
        languages.add("kotlin")
        entry_points.append("app/src/main")
    elif list(root.glob("*.xcodeproj")) or (root / "Package.swift").exists():
        stack_type = "swift"
        languages.add("swift")
        entry_points.append("Package.swift")
    elif (root / "pubspec.yaml").exists():
        stack_type = "flutter"
        languages.add("dart")
        entry_points.append("lib/main.dart")
    elif (root / "index.html").exists() and not (root / "package.json").exists():
        stack_type = "static-html"
        languages.add("html")
        entry_points.append("index.html")

    if (root / "docker-compose.yml").exists() or (root / "Dockerfile").exists():
        pass
    has_docker = (root / "docker-compose.yml").exists() or (root / "Dockerfile").exists()
    has_git = (root / ".git").exists()
    has_tests = any(
        [
            (root / "tests").is_dir(),
            (root / "test").is_dir(),
            (root / "phpunit.xml").exists(),
            (root / "jest.config.js").exists(),
            (root / "vitest.config.ts").exists(),
        ]
    )

    if (root / ".env.example").exists():
        env_text = (root / ".env.example").read_text(encoding="utf-8", errors="ignore").lower()
        if "postgres" in env_text or "postgresql" in env_text:
            database = "postgres"
        elif "mysql" in env_text or "mariadb" in env_text:
            database = "mysql"
        elif "sqlite" in env_text:
            database = "sqlite"

    completeness = _estimate_completeness(root, has_tests=has_tests, has_git=has_git, has_docker=has_docker)
    return StackReport(
        stack_type=stack_type,
        languages=sorted(languages),
        dependencies=dependencies,
        database=database,
        entry_points=entry_points,
        has_tests=has_tests,
        has_docker=has_docker,
        has_git=has_git,
        estimated_completeness=completeness,
    )


def _estimate_completeness(root: Path, *, has_tests: bool, has_git: bool, has_docker: bool) -> int:
    score = 20
    if (root / "README.md").exists():
        score += 10
    if has_git:
        score += 10
    if has_tests:
        score += 20
    if has_docker:
        score += 10
    if (root / ".env.example").exists():
        score += 10
    source_dirs = sum(1 for name in ("src", "app", "modules", "includes") if (root / name).is_dir())
    score += min(20, source_dirs * 5)
    return min(100, score)


def project_tree(project_path: Path, *, depth: int = 2) -> list[dict[str, str]]:
    root = project_path.resolve()
    rows: list[dict[str, str]] = []

    def walk(current: Path, level: int) -> None:
        if level > depth:
            return
        try:
            children = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return
        for child in children:
            if child.name.startswith(".") and child.name not in {".env.example"}:
                continue
            rel = str(child.relative_to(root))
            rows.append({"path": rel, "type": "dir" if child.is_dir() else "file"})
            if child.is_dir():
                walk(child, level + 1)

    walk(root, 0)
    return rows[:500]
