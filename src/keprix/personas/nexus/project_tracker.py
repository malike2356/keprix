"""Project state and milestone tracking backed by playbook runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from keprix.compat import UTC
from pathlib import Path
from typing import Any

from keprix.personas.ember.coach import WELLBEING_LANE_AGENTS, is_wellbeing_lane_owner


@dataclass(slots=True)
class Milestone:
    id: str
    title: str
    status: str = "pending"
    deadline: str | None = None
    owner: str = "NEXUS"
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "deadline": self.deadline,
            "owner": self.owner,
            "dependencies": list(self.dependencies),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Milestone:
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            status=str(data.get("status", "pending")),
            deadline=data.get("deadline"),
            owner=str(data.get("owner", "NEXUS")),
            dependencies=list(data.get("dependencies", [])),
        )


@dataclass
class ProjectState:
    workspace_id: str
    project_name: str = "Untitled Project"
    milestones: list[Milestone] = field(default_factory=list)
    agent_status: dict[str, str] = field(default_factory=dict)
    blockers: list[dict[str, Any]] = field(default_factory=list)

    def to_playbook_state(self) -> dict[str, Any]:
        return {
            "project": {
                "workspace_id": self.workspace_id,
                "project_name": self.project_name,
                "milestones": [m.to_dict() for m in self.milestones],
                "agent_status": dict(self.agent_status),
                "blockers": list(self.blockers),
            }
        }

    @classmethod
    def from_playbook_state(cls, state: dict[str, Any]) -> ProjectState:
        project = state.get("project", state)
        milestones = [Milestone.from_dict(row) for row in project.get("milestones", [])]
        return cls(
            workspace_id=str(project.get("workspace_id", "default")),
            project_name=str(project.get("project_name", "Untitled Project")),
            milestones=milestones,
            agent_status=dict(project.get("agent_status", {})),
            blockers=list(project.get("blockers", [])),
        )

    def overall_status(self) -> str:
        if self.blockers:
            return "blocked"
        if not self.milestones:
            return "not_started"
        statuses = {m.status for m in self.milestones}
        if statuses == {"completed"}:
            return "completed"
        if "in_progress" in statuses or "completed" in statuses:
            return "in_progress"
        return "not_started"

    def detect_blockers(self) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        completed_ids = {m.id for m in self.milestones if m.status == "completed"}
        now = datetime.now(UTC)

        for milestone in self.milestones:
            if milestone.status == "blocked":
                found.append(
                    {
                        "type": "milestone_blocked",
                        "milestone_id": milestone.id,
                        "title": milestone.title,
                        "owner": milestone.owner,
                    }
                )
            for dep_id in milestone.dependencies:
                if dep_id not in completed_ids and milestone.status in {"in_progress", "pending"}:
                    found.append(
                        {
                            "type": "dependency_blocked",
                            "milestone_id": milestone.id,
                            "title": milestone.title,
                            "blocked_by": dep_id,
                        }
                    )
            if milestone.deadline and milestone.status != "completed":
                try:
                    deadline = datetime.fromisoformat(milestone.deadline.replace("Z", "+00:00"))
                    if deadline < now:
                        found.append(
                            {
                                "type": "deadline_passed",
                                "milestone_id": milestone.id,
                                "title": milestone.title,
                                "deadline": milestone.deadline,
                            }
                        )
                except ValueError:
                    continue

        self.blockers = found
        return found

    def generate_status_report(self) -> str:
        template_path = Path(__file__).resolve().parent / "prompts" / "status.md"
        template = template_path.read_text(encoding="utf-8")
        self.detect_blockers()

        milestone_rows = "\n".join(
            f"| {m.title} | {m.status} | {m.deadline or '-'} | {m.owner} |"
            for m in self.milestones
            if not is_wellbeing_lane_owner(m.owner)
        ) or "| (none) | - | - | - |"

        if self.blockers:
            blockers_section = "\n".join(
                f"- **{b['type']}**: {b.get('title', b.get('milestone_id', 'unknown'))}" for b in self.blockers
            )
        else:
            blockers_section = "No active blockers."

        agent_rows = "\n".join(
            f"| {agent} | {status} | now |"
            for agent, status in sorted(self.agent_status.items())
            if agent.upper() not in WELLBEING_LANE_AGENTS
        )
        if not agent_rows:
            agent_rows = "| (none) | idle | - |"

        next_actions = []
        for milestone in self.milestones:
            if is_wellbeing_lane_owner(milestone.owner):
                continue
            if milestone.status in {"pending", "in_progress"}:
                next_actions.append(f"- Complete milestone: {milestone.title} ({milestone.owner})")
        if not next_actions:
            next_actions.append("- No pending milestones.")

        replacements = {
            "{{project_name}}": self.project_name,
            "{{workspace_id}}": self.workspace_id,
            "{{generated_at}}": datetime.now(UTC).isoformat(),
            "{{overall_status}}": self.overall_status(),
            "{{summary}}": f"{len(self.milestones)} milestone(s), {len(self.blockers)} blocker(s).",
            "{{milestone_rows}}": milestone_rows,
            "{{blockers_section}}": blockers_section,
            "{{agent_rows}}": agent_rows,
            "{{next_actions}}": "\n".join(next_actions),
        }

        report = template
        for key, value in replacements.items():
            report = report.replace(key, value)
        return report
