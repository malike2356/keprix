"""Prompt 275 level-up template tests."""

from __future__ import annotations

from keprix.agent_os.level_up_templates import actions_from_export


def test_level_up_actions_sort_high_leverage_first() -> None:
    export = {
        "top_gaps": [
            {"title": "Create one active cron cadence", "dimension": "cadence", "leverage": 60},
            {"title": "Add context/about-business.md", "dimension": "context", "leverage": 90},
            {"title": "Create connections.md with tier-1 domains", "dimension": "connections", "leverage": 80},
        ]
    }

    actions = actions_from_export(export)

    assert actions[0].leverage == "high"
    assert actions[0].dimension == "context"
    assert actions[-1].dimension == "cadence"
