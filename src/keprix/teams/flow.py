"""Deterministic flow model backed by the playbook runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.playbook.runtime import END, PlaybookGraph, PlaybookInterrupt, interrupt
from keprix.teams.crew import Crew
from keprix.teams.task import TeamTask


@dataclass(slots=True)
class TeamFlow:
    name: str
    start: str
    events: dict[str, list[str]] = field(default_factory=dict)

    def compile_to_playbook(self, crew: Crew) -> PlaybookGraph:
        tasks_by_id = {task.id: task for task in crew.tasks}
        if self.start not in tasks_by_id:
            raise ValueError(f"Unknown flow start task: {self.start}")

        graph = PlaybookGraph(self.name)

        for task in crew.order_tasks():
            graph.add_node(task.id, self._handler_for_task(crew, task))

        graph.set_entry(self.start)
        ordered_ids = [task.id for task in crew.order_tasks()]
        for index, task_id in enumerate(ordered_ids):
            next_task = ordered_ids[index + 1] if index + 1 < len(ordered_ids) else END
            graph.add_edge(task_id, next_task)
        return graph

    @staticmethod
    def _handler_for_task(crew: Crew, task: TeamTask):
        async def _handler(state: dict[str, Any]) -> dict[str, Any]:
            if task.human_review and task.id not in set(state.get("approved_tasks") or []):
                crew.hooks.emit(
                    "on_approval_request",
                    crew=crew.name,
                    task_id=task.id,
                    risk_level=task.risk_level,
                )
                interrupt(
                    f"Task {task.id} requires human review",
                    approval_request={"task_id": task.id, "risk_level": task.risk_level},
                )
            new_state = dict(state)
            new_state.setdefault("task_results", {})
            result = await crew.run_task(task, new_state)
            new_state["task_results"][task.id] = result.to_dict()
            if result.artifact:
                new_state.setdefault("artifacts", {})[result.artifact] = result.output
            new_state["last_task"] = task.id
            return new_state

        return _handler
