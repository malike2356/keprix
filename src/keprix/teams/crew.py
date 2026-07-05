"""Role-based crew execution."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from keprix.teams.agent_role import AgentRole, DEFAULT_ROLES
from keprix.teams.guardrails import GuardrailCallable, run_guardrails
from keprix.teams.hooks import HookManager
from keprix.teams.structured_output import validate_structured_output
from keprix.teams.task import TaskResult, TeamTask

TaskExecutor = Callable[[AgentRole, TeamTask, dict[str, Any]], Any]


class CrewError(RuntimeError):
    pass


class Crew:
    def __init__(
        self,
        *,
        name: str,
        roles: dict[str, AgentRole] | None = None,
        tasks: list[TeamTask] | None = None,
        hooks: HookManager | None = None,
        executor: TaskExecutor | None = None,
        guardrails: dict[str, list[GuardrailCallable]] | None = None,
    ) -> None:
        self.name = name
        self.roles = {**DEFAULT_ROLES, **(roles or {})}
        self.tasks = list(tasks or [])
        self.hooks = hooks or HookManager()
        self.executor = executor or self._default_executor
        self.guardrails = guardrails or {}

    async def run(self, objective: str, initial_state: dict[str, Any] | None = None) -> dict[str, Any]:
        state = dict(initial_state or {})
        state.setdefault("objective", objective)
        state.setdefault("task_results", {})
        ordered = self.order_tasks()
        for task in ordered:
            result = await self.run_task(task, state)
            state["task_results"][task.id] = result.to_dict()
            if result.artifact:
                state.setdefault("artifacts", {})[result.artifact] = result.output
        return state

    async def run_task(self, task: TeamTask, state: dict[str, Any]) -> TaskResult:
        role = self.roles.get(task.role)
        if role is None:
            raise CrewError(f"Unknown role for task {task.id}: {task.role}")

        self._check_dependencies(task, state)
        self.hooks.emit("before_task", crew=self.name, task_id=task.id, role=role.name)

        delegated_to = None
        effective_role = role
        if task.allow_delegation and role.can_delegate():
            delegated_to = self._choose_delegate(task)
            if delegated_to and delegated_to in self.roles:
                effective_role = self.roles[delegated_to]

        attempts = max(1, task.retry_policy.max_attempts)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                output = await self._call_executor(effective_role, task, state)
                validate_structured_output(output, task.output_schema)
                guardrail_result = run_guardrails(output, self.guardrails.get(task.id))
                if not guardrail_result.passed:
                    raise CrewError(guardrail_result.message)
                artifact = task.output_artifact or self._artifact_from_task(task)
                self.hooks.emit(
                    "artifact_write",
                    crew=self.name,
                    task_id=task.id,
                    artifact=artifact,
                )
                result = TaskResult(
                    task_id=task.id,
                    role=effective_role.name,
                    output=output,
                    artifact=artifact,
                    attempts=attempt,
                    delegated_to=delegated_to,
                )
                self.hooks.emit("after_task", crew=self.name, task_id=task.id, result=result.to_dict())
                return result
            except Exception as exc:
                last_error = exc
                self.hooks.emit("on_error", crew=self.name, task_id=task.id, error=str(exc))
                if attempt >= attempts:
                    break
        raise CrewError(f"Task {task.id} failed after {attempts} attempts: {last_error}")

    def order_tasks(self) -> list[TeamTask]:
        by_id = {task.id: task for task in self.tasks}
        ordered: list[TeamTask] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visited:
                return
            if task_id in visiting:
                raise CrewError(f"Task dependency cycle at {task_id}")
            if task_id not in by_id:
                raise CrewError(f"Unknown task dependency: {task_id}")
            visiting.add(task_id)
            for dependency in by_id[task_id].dependencies:
                visit(dependency)
            visiting.remove(task_id)
            visited.add(task_id)
            ordered.append(by_id[task_id])

        for task in self.tasks:
            visit(task.id)
        return ordered

    def _check_dependencies(self, task: TeamTask, state: dict[str, Any]) -> None:
        results = state.get("task_results", {})
        missing = [dependency for dependency in task.dependencies if dependency not in results]
        if missing:
            raise CrewError(f"Task {task.id} missing dependencies: {', '.join(missing)}")

    def _choose_delegate(self, task: TeamTask) -> str | None:
        if "review" in task.description.lower() and "qa_reviewer" in self.roles:
            return "qa_reviewer"
        return None

    async def _call_executor(
        self,
        role: AgentRole,
        task: TeamTask,
        state: dict[str, Any],
    ) -> Any:
        self.hooks.emit("on_tool_call", crew=self.name, task_id=task.id, role=role.name)
        result = self.executor(role, task, state)
        if inspect.isawaitable(result):
            return await result
        return result

    @staticmethod
    def _default_executor(role: AgentRole, task: TeamTask, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "role": role.name,
            "task": task.id,
            "objective": state.get("objective", ""),
            "summary": task.expected_output or task.description,
        }

    @staticmethod
    def _artifact_from_task(task: TeamTask) -> str | None:
        if task.expected_output and "." in task.expected_output and " " not in task.expected_output:
            return task.expected_output
        return None
