"""Scheduled run tests (Prompt 61)."""

from __future__ import annotations

import pytest

from keprix.control_center.scheduled_runs import create_scheduled_automation, schedule_playbook_run
from keprix.control_center.store import ControlCenterStore, reset_control_center_store


@pytest.fixture
def store(tmp_path):
    reset_control_center_store(ControlCenterStore(base_dir=tmp_path / "control_center"))
    yield
    reset_control_center_store(None)


def test_schedule_playbook_run_enqueues_work(store):
    automation = create_scheduled_automation(
        name="morning-playbook",
        playbook_id="starter-team",
        schedule_cron="0 9 * * *",
    )
    run = schedule_playbook_run(automation["id"])
    assert run is not None
    assert run["status"] == "queued"
    assert run["payload"]["playbook_id"] == "starter-team"
    assert run["payload"]["trigger"] == "schedule"

    again = schedule_playbook_run(automation["id"])
    assert again is not None
    assert again["id"] != run["id"]
