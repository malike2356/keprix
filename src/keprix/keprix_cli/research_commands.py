"""Research workspace CLI commands."""

from __future__ import annotations

import json

from keprix.research_workspace.playbook_runner import ResearchPlaybookRunner, list_playbook_specs
from keprix.research_workspace.project import ResearchProjectService
from keprix.research_workspace.store import get_research_workspace_store


def cmd_research_list(args) -> int:
    items = list_playbook_specs()
    print(json.dumps({"playbooks": items}, indent=2))
    return 0


def cmd_research_run(args) -> int:
    store = get_research_workspace_store(workspace_id=getattr(args, "workspace_id", "default"))
    runner = ResearchPlaybookRunner(store)
    result = runner.run(
        args.project_id,
        args.playbook_id,
        owner="cli",
        dry_run=bool(args.dry_run),
        parameters={},
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_research_projects(args) -> int:
    store = get_research_workspace_store(workspace_id=getattr(args, "workspace_id", "default"))
    projects = ResearchProjectService(store).list()
    print(
        json.dumps(
            {"items": [project.to_dict() for project in projects]},
            indent=2,
            default=str,
        )
    )
    return 0
