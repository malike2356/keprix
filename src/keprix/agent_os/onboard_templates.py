"""Templates for the Agent OS onboard interview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

QUESTIONS: tuple[dict[str, str], ...] = (
    {"key": "q1", "file": "context/about-business.md", "prompt": "Who are you, what do you sell, and who is your ICP?"},
    {"key": "q2", "file": "context/writing-samples.md", "prompt": "Paste 1-2 recent writing samples verbatim."},
    {"key": "q3", "file": "context/priorities.md", "prompt": "What are your top 2-3 priorities for the next 90 days?"},
    {"key": "q4", "file": "context/about-me.md", "prompt": "What are your biggest pains or bottlenecks?"},
    {"key": "q5", "file": "connections.md", "prompt": "What tools do you use daily?"},
    {"key": "q6", "file": "context/guardrails.md", "prompt": "What should the agent never do?"},
    {"key": "q7", "file": "context/cadence-preferences.md", "prompt": "What working cadence do you prefer?"},
)


def question_payload() -> list[dict[str, str]]:
    return [dict(question, number=str(index)) for index, question in enumerate(QUESTIONS, start=1)]


def render_context_files(answers: dict[str, str]) -> dict[str, str]:
    return {
        "context/about-business.md": "# About Business\n\n" + answers.get("q1", "").strip() + "\n",
        "context/writing-samples.md": "# Writing Samples\n\n" + answers.get("q2", "").strip() + "\n",
        "context/priorities.md": "# Priorities\n\n## Next 90 days\n\n" + answers.get("q3", "").strip() + "\n",
        "context/about-me.md": "# About Me\n\n## Pains and bottlenecks\n\n" + answers.get("q4", "").strip() + "\n",
        "context/guardrails.md": "# Guardrails\n\n" + answers.get("q6", "").strip() + "\n",
        "context/cadence-preferences.md": "# Cadence Preferences\n\n" + answers.get("q7", "").strip() + "\n",
        "connections.md": render_connections_draft(answers.get("q5", "")),
        "context/intake.json": json.dumps({"answers": answers, "question_count": len(QUESTIONS)}, indent=2) + "\n",
    }


def render_connections_draft(tools_text: str) -> str:
    tools = [line.strip("-* 	") for line in tools_text.replace(",", "\n").splitlines() if line.strip()]
    rows = "\n".join(f"- {tool}: status: draft" for tool in tools) or "- Add daily tools here: status: draft"
    return "# Connections\n\n## Daily tools draft\n\n" + rows + "\n"


def write_onboard_files(root: Path, answers: dict[str, str]) -> dict[str, str]:
    output: dict[str, str] = {}
    for rel, content in render_context_files(answers).items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        output[rel] = str(path)
    return output
