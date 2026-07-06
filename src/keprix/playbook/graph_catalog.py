"""Built-in playbook graph templates for the workspace UI."""

from __future__ import annotations

from typing import Any

PLAYBOOK_GRAPH_CATALOG: list[dict[str, Any]] = [
    {
        "graph_id": "sdk-workflow",
        "title": "SDK workflow",
        "description": "Prepare, branch, human approval, and artifact export (TypeScript SDK parity).",
        "entry": "prepare",
        "steps": [
            {"id": "prepare", "type": "task", "config": {"key": "topic", "value": "sdk-workflow"}},
            {
                "id": "route",
                "type": "branch",
                "config": {"key": "topic", "equals": "sdk-workflow"},
            },
            {
                "id": "approve",
                "type": "approval",
                "config": {
                    "message": "Publish workflow artifact?",
                    "risk": "low",
                    "summary": "SDK workflow publish gate",
                },
            },
            {
                "id": "report",
                "type": "artifact",
                "config": {
                    "name": "workflow-report",
                    "from_key": "prepare_output",
                    "content": "Workflow complete",
                },
            },
        ],
        "edges": [
            {"from": "route", "to": "approve", "when": "true"},
            {"from": "approve", "to": "report"},
        ],
    },
    {
        "graph_id": "research-deep-dive",
        "title": "Research deep dive",
        "description": "Load a research topic, draft a summary, and export a cited artifact.",
        "entry": "intake",
        "steps": [
            {
                "id": "intake",
                "type": "task",
                "config": {"key": "research_topic", "value": "pending", "message": "Research topic loaded"},
            },
            {
                "id": "summarize",
                "type": "task",
                "config": {"key": "summary_status", "value": "drafted", "message": "Summary drafted"},
            },
            {
                "id": "publish",
                "type": "artifact",
                "config": {"name": "research-brief", "from_key": "summarize_output"},
            },
        ],
        "edges": [],
    },
    {
        "graph_id": "opportunity-scan",
        "title": "Opportunity scan",
        "description": "Scan signals, score opportunities, and stage a review artifact.",
        "entry": "scan",
        "steps": [
            {
                "id": "scan",
                "type": "task",
                "config": {"key": "scan_status", "value": "complete", "message": "Signals collected"},
            },
            {
                "id": "score",
                "type": "task",
                "config": {"key": "score_status", "value": "ranked", "message": "Opportunities ranked"},
            },
            {
                "id": "review",
                "type": "approval",
                "config": {
                    "message": "Approve opportunity shortlist?",
                    "risk": "medium",
                    "summary": "Opportunity scan review",
                },
            },
            {
                "id": "export",
                "type": "artifact",
                "config": {"name": "opportunity-shortlist", "from_key": "score_output"},
            },
        ],
        "edges": [
            {"from": "review", "to": "export"},
        ],
    },
    {
        "graph_id": "crew-flow",
        "title": "Agent team crew flow",
        "description": "Execute a registered YAML agent team inside a durable playbook graph.",
        "entry": "execute",
        "steps": [
            {
                "id": "execute",
                "type": "crew_execute",
                "config": {
                    "team_id": "sample-crew",
                    "objective": "Run the registered crew objective",
                },
            },
        ],
        "edges": [],
    },
    {
        "graph_id": "browser-flow",
        "title": "Browser dry-run flow",
        "description": "Run a governed browser skill inside a disposable harness session.",
        "entry": "browse",
        "steps": [
            {
                "id": "browse",
                "type": "browser_action",
                "config": {
                    "skill": "checkout_dry_run",
                    "objective": "Adoption browser dry run",
                    "profile_kind": "disposable",
                    "approved": True,
                },
            },
        ],
        "edges": [],
    },
    {
        "graph_id": "data-analysis",
        "title": "Data analysis",
        "description": "Ingest CSV data and run a short analytics code step in one playbook.",
        "entry": "ingest",
        "steps": [
            {
                "id": "ingest",
                "type": "analytics_ingest",
                "config": {
                    "dataset_name": "main",
                    "data": "name,score\nAlice,85\nBob,92",
                },
            },
            {
                "id": "summarize",
                "type": "analytics_code",
                "config": {
                    "dataset_name": "main",
                    "code": "result = {'row_count': row_count, 'dataset': dataset_name}",
                },
            },
        ],
        "edges": [],
    },
]


def get_graph_template(graph_id: str) -> dict[str, Any] | None:
    for item in PLAYBOOK_GRAPH_CATALOG:
        if item["graph_id"] == graph_id:
            return item
    return None
