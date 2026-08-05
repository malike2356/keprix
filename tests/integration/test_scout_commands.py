"""Integration tests for Scout command handling."""

from __future__ import annotations

import json

import pytest

from keprix.governance.kill_relay import agent_stop_requested, clear_kill_state
from keprix.governance.policy_receiver import get_policy_registry
from keprix.security.scout_config import ScoutConfig
from keprix.security.scout_control import egress_force_blocked, reset_scout_control
from keprix.security.scout_listener import ScoutListener
from keprix.security.scout_types import ScoutCommand


@pytest.fixture(autouse=True)
def _reset():
    clear_kill_state()
    reset_scout_control()
    get_policy_registry().reload_from_store([])
    yield
    clear_kill_state()
    reset_scout_control()


def _listener() -> ScoutListener:
    return ScoutListener(
        ScoutConfig(
            enabled=True,
            api_key="key",
            endpoint="https://scout.example.test",
            redis_url="redis://localhost:6379/0",
            agent_id="instance-test",
            product="keprix",
        )
    )


@pytest.mark.asyncio
async def test_suspend_and_resume_commands():
    listener = _listener()
    await listener.handle_message(
        json.dumps(
            {
                "command_id": "cmd-suspend",
                "command": ScoutCommand.SUSPEND.value,
                "agent_id": "instance-test",
                "params": {},
                "issued_by": "test",
                "issued_at": "2026-07-10T00:00:00+00:00",
            }
        )
    )
    assert agent_stop_requested() is True

    await listener.handle_message(
        json.dumps(
            {
                "command_id": "cmd-resume",
                "command": ScoutCommand.RESUME.value,
                "agent_id": "instance-test",
                "params": {},
                "issued_by": "test",
                "issued_at": "2026-07-10T00:00:00+00:00",
            }
        )
    )
    assert agent_stop_requested() is False


@pytest.mark.asyncio
async def test_quarantine_tool_command():
    listener = _listener()
    await listener.handle_message(
        json.dumps(
            {
                "command_id": "cmd-quarantine",
                "command": ScoutCommand.QUARANTINE_TOOL.value,
                "agent_id": "*",
                "params": {"tool_name": "terminal"},
                "issued_by": "test",
                "issued_at": "2026-07-10T00:00:00+00:00",
            }
        )
    )
    assert get_policy_registry().is_tool_blocked("terminal") is True


@pytest.mark.asyncio
async def test_block_egress_command():
    listener = _listener()
    await listener.handle_message(
        json.dumps(
            {
                "command_id": "cmd-egress",
                "command": ScoutCommand.BLOCK_EGRESS.value,
                "agent_id": "*",
                "params": {},
                "issued_by": "test",
                "issued_at": "2026-07-10T00:00:00+00:00",
            }
        )
    )
    assert egress_force_blocked() is True
