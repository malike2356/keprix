"""Prompt 276 onboard template tests."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.agent_os.onboard_templates import render_context_files, write_onboard_files


def answers() -> dict[str, str]:
    return {
        "q1": "We sell analytics to schools. ICP is operations leaders.",
        "q2": "Verbatim writing sample.",
        "q3": "Launch pilot. Improve retention.",
        "q4": "Manual reporting bottleneck.",
        "q5": "Gmail, Calendar\nDrive",
        "q6": "Never email customers without approval.",
        "q7": "Weekly sprint.",
    }


def test_render_context_files_contains_intake_and_connections() -> None:
    files = render_context_files(answers())

    assert "context/intake.json" in files
    assert "Gmail: status: draft" in files["connections.md"]
    assert json.loads(files["context/intake.json"])["answers"]["q1"].startswith("We sell")


def test_write_onboard_files_writes_context_tree(tmp_path: Path) -> None:
    output = write_onboard_files(tmp_path, answers())

    assert (tmp_path / "context" / "about-business.md").is_file()
    assert (tmp_path / "connections.md").is_file()
    assert output["context/guardrails.md"].endswith("context/guardrails.md")
