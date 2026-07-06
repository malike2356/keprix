"""Playbook analytics node tests (Prompt 197)."""

from __future__ import annotations

import pytest

from keprix.playbook.graph_catalog import get_graph_template
from keprix.playbook.sdk_workflow import start_workflow_run


@pytest.mark.asyncio
async def test_data_analysis_template_runs_ingest_and_code() -> None:
    template = get_graph_template("data-analysis")
    assert template is not None

    run = await start_workflow_run(
        template,
        workspace_id="analytics-playbook-test",
        initial_state={},
    )
    assert run.status.value == "completed"
    assert run.state["analytics_ingest"]["row_count"] == 2
    assert run.state["analytics_result"]["ok"] is True
    assert run.state["analytics_session_id"]
