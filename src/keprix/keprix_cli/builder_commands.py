"""Builder CLI commands (Prompt 29)."""

from __future__ import annotations

import json

from keprix.backend.builder.build_agent import start_build_job
from keprix.backend.builder.registry import get_project_registry
from keprix.backend.builder.store import get_builder_store
from keprix.backend.builder.templates.engine import scaffold_project
from keprix.backend.builder.tools import deploy_to_docker, deploy_to_lampp


def _find_project(name: str) -> dict:
    registry = get_project_registry()
    rows = registry.list_projects()
    for row in rows:
        if row.get("name") == name or row.get("id") == name:
            return row
    raise SystemExit(f"Project not found: {name}")


def cmd_builder_list(args) -> int:
    rows = get_project_registry().list_projects()
    print(json.dumps({"projects": rows}, indent=2))
    return 0


def cmd_builder_analyse(args) -> int:
    project = _find_project(args.name)
    report = get_project_registry().analyse(project["id"])
    print(json.dumps(report, indent=2))
    return 0


def cmd_builder_build(args) -> int:
    project = _find_project(args.name)
    job = get_builder_store().create_job(
        {
            "project_id": project["id"],
            "job_type": "add-feature",
            "instruction": args.instruction,
        }
    )
    start_build_job(job["id"])
    print(json.dumps({"job": job}, indent=2))
    return 0


def cmd_builder_scaffold(args) -> int:
    path = getattr(args, "path", None) or "/tmp/keprix-scaffolds"
    result = scaffold_project(template=args.template, name=args.name, path=path, config={})
    print(json.dumps(result, indent=2))
    return 0


def cmd_builder_status(args) -> int:
    job = get_builder_store().get_job(args.job_id)
    if job is None:
        raise SystemExit(f"Job not found: {args.job_id}")
    print(json.dumps({"job": job}, indent=2))
    return 0


def cmd_builder_logs(args) -> int:
    log = get_builder_store().read_job_log(args.job_id)
    print(log)
    return 0


def cmd_builder_deploy(args) -> int:
    project = _find_project(args.name)
    target = getattr(args, "target", "lampp")
    if target == "docker":
        result = deploy_to_docker(project["path"])
    else:
        result = deploy_to_lampp(project["path"])
    print(json.dumps(result, indent=2))
    return 0
