"""Tests for browser_action playbook node (Prompt 196)."""

from __future__ import annotations

import pytest

from keprix.playbook.sdk_workflow import start_workflow_run


@pytest.mark.asyncio
async def test_browser_action_playbook_completes() -> None:
    run = await start_workflow_run(
        {
            "graph_id": "browser-flow-test",
            "entry": "browse",
            "steps": [
                {
                    "id": "browse",
                    "type": "browser_action",
                    "config": {
                        "skill": "checkout_dry_run",
                        "objective": "Playbook browser dry run",
                        "profile_kind": "disposable",
                        "approved": True,
                    },
                },
            ],
            "edges": [],
        },
        workspace_id="browser-playbook-test",
        initial_state={"workspace_id": "browser-playbook-test"},
    )
    assert run.status.value == "completed"
    assert "browser_result" in run.state
    assert run.state["browser_result"]["skill"] == "checkout_dry_run"
    assert run.state["browser_result"]["dry_run"] is True
    assert run.state["browser_result"]["mode"] == "dry_run"
