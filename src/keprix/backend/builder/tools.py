"""Builder agent tools (Prompt 29)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from keprix.backend.builder.build_agent import git_project_status
from keprix.backend.builder.registry import get_project_registry
from keprix.backend.builder.stack_detector import detect_stack, project_tree
from keprix.backend.builder.templates.engine import scaffold_project
from keprix.coding.lint_test_runner import detect_lint_command, detect_test_command, run_lint, run_tests


def project_analyse(project_path: str | Path) -> dict[str, Any]:
    path = Path(project_path).resolve()
    report = detect_stack(path)
    lint_cmd = detect_lint_command(path)
    lint_output = run_lint(path, lint_cmd).output if lint_cmd else "lint skipped"
    audit_output = _dependency_audit(path, report.stack_type)
    return {
        "stack_report": report.to_dict(),
        "tree_sample": project_tree(path, depth=2)[:80],
        "lint": lint_output,
        "dependency_audit": audit_output,
        "git": git_project_status(path),
    }


def project_scaffold(template: str, name: str, path: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    return scaffold_project(template=template, name=name, path=path, config=config or {})


def file_write_project(project_path: str | Path, relative_path: str, content: str) -> dict[str, Any]:
    root = Path(project_path).resolve()
    target = (root / relative_path).resolve()
    if root not in target.parents and target != root:
        raise ValueError("Path escapes project directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": str(target), "bytes": len(content.encode("utf-8"))}


def run_project_tests(project_path: str | Path) -> dict[str, Any]:
    path = Path(project_path)
    cmd = detect_test_command(path)
    if not cmd:
        return {"ran": False, "summary": "no test command detected"}
    result = run_tests(path, cmd)
    return {"ran": True, "command": cmd, "summary": result.output, "passed": result.ok}


def deploy_to_lampp(project_path: str | Path) -> dict[str, Any]:
    path = Path(project_path).resolve()
    htdocs_raw = os.environ.get("KEPRIX_LAMPP_HTDOCS", "").strip()
    if not htdocs_raw:
        return {
            "ok": False,
            "message": "Set KEPRIX_LAMPP_HTDOCS to your Apache document root (optional local deploy target)",
        }
    htdocs = Path(htdocs_raw).expanduser()
    if not htdocs.is_dir():
        return {"ok": False, "message": f"KEPRIX_LAMPP_HTDOCS is not a directory: {htdocs}"}
    link_name = path.name
    link_path = htdocs / link_name
    if not link_path.exists():
        link_path.symlink_to(path)
    url = f"http://localhost/{link_name}/"
    return {"ok": True, "url": url, "symlink": str(link_path)}


def deploy_to_docker(project_path: str | Path) -> dict[str, Any]:
    path = Path(project_path)
    dockerfile = path / "Dockerfile"
    if not dockerfile.exists():
        return {"ok": False, "message": "Dockerfile not found"}
    image = f"keprix-{path.name}:latest".lower()
    build = subprocess.run(["docker", "build", "-t", image, "."], cwd=str(path), capture_output=True, text=True)
    if build.returncode != 0:
        return {"ok": False, "message": (build.stderr or build.stdout)[:2000]}
    run = subprocess.run(
        ["docker", "run", "-d", "-p", "0:8080", image],
        capture_output=True,
        text=True,
    )
    if run.returncode != 0:
        return {"ok": False, "message": (run.stderr or run.stdout)[:2000]}
    return {"ok": True, "image": image, "container_id": run.stdout.strip(), "url": "http://localhost:8080"}


def add_keprix_sdk(project_path: str | Path, project_name: str) -> dict[str, Any]:
    path = Path(project_path)
    domains_path = path / "src" / "keprix" / "domains.ts"
    if domains_path.exists():
        return {"ok": True, "message": "SDK domains file already exists", "path": str(domains_path)}
    from keprix.backend.builder.templates.engine import _domains_ts

    content = _domains_ts(project_name, {})
    file_write_project(path, "src/keprix/domains.ts", content)
    return {"ok": True, "path": str(domains_path)}


def enrol_governance(project_path: str | Path) -> dict[str, Any]:
    registry = get_project_registry()
    row = registry._store.get_project_by_path(str(Path(project_path).resolve()))
    if row is None:
        return {"ok": False, "message": "project not in registry"}
    updated = registry._store.upsert_project({**row, "governance_enrolled": True})
    return {"ok": True, "project": updated}


def _dependency_audit(path: Path, stack_type: str) -> str:
    if stack_type in {"nextjs", "nuxt", "react", "node-express"} and (path / "package.json").exists():
        proc = subprocess.run(["npm", "audit", "--json"], cwd=str(path), capture_output=True, text=True)
        return (proc.stdout or proc.stderr or "npm audit unavailable")[:4000]
    if stack_type in {"laravel", "custom-php", "wordpress"} and (path / "composer.json").exists():
        proc = subprocess.run(["composer", "audit", "--format=json"], cwd=str(path), capture_output=True, text=True)
        return (proc.stdout or proc.stderr or "composer audit unavailable")[:4000]
    return "audit skipped"
