"""Static Workflow Coach rules for Studio."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CoachSuggestion:
    node_type: str
    label: str
    reason: str
    prefilled_data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def suggest_next_nodes(
    *,
    selected_node_type: str | None,
    canvas: dict[str, Any],
) -> list[CoachSuggestion]:
    del canvas
    if selected_node_type == "trigger":
        return [
            CoachSuggestion("agent_task", "Add agent task", "Start by asking an agent to gather or transform data.", {"label": "Agent task", "prompt": "Use {{ state.query }} to gather context", "tools": []}),
            CoachSuggestion("http", "Call an API", "Fetch data from an external service before agent processing.", {"label": "HTTP request", "url": "https://api.example.com", "method": "GET"}),
        ]
    if selected_node_type == "agent_task":
        return [
            CoachSuggestion("condition", "Branch on result", "Route high-risk or low-confidence outputs differently.", {"label": "Check result", "expression": "score > 70"}),
            CoachSuggestion("http", "Send to API", "Forward the agent output to a webhook or service.", {"label": "Send result", "url": "https://api.example.com", "method": "POST"}),
            CoachSuggestion("human_approval", "Ask for approval", "Pause before a risky external action.", {"label": "Approval", "message": "Approve this result?", "risk": "medium"}),
        ]
    if selected_node_type == "condition":
        return [
            CoachSuggestion("agent_task", "True branch task", "Handle the true branch with a focused agent task.", {"label": "Handle true branch", "prompt": "Act on the true branch", "tools": []}),
            CoachSuggestion("human_approval", "Approval branch", "Require human review for the high-risk branch.", {"label": "Approval", "message": "Review this branch", "risk": "high"}),
        ]
    if selected_node_type == "human_approval":
        return [
            CoachSuggestion("agent_task", "Send approved output", "Continue after approval with a final agent action.", {"label": "Send output", "prompt": "Send the approved output", "tools": []}),
            CoachSuggestion("artifact", "Create artifact", "Capture an auditable output after approval.", {"label": "Export artifact", "name": "result"}),
        ]
    return [
        CoachSuggestion("trigger", "Start with trigger", "Every Studio playbook needs a trigger.", {"label": "Trigger"}),
        CoachSuggestion("agent_task", "Add agent task", "Agent tasks are the main unit of playbook work.", {"label": "Agent task", "prompt": "Describe the task", "tools": []}),
    ]
