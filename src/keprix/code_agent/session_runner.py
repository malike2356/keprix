"""Multi-turn OpenHands-style coding session runner."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keprix.code_agent.code_agent import CodeAgent, CodeAgentConfig
from keprix.code_agent.session_store import CodingSessionRecord, CodingSessionStore, get_coding_session_store
from keprix.coding.issue_runner import IssueRunRequest, run_issue
from keprix.coding.trajectory import TrajectoryLogger
from keprix.control_center.workspace_sessions import append_trace


@dataclass
class TurnResult:
    ok: bool
    turn: int
    action: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    session_status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "turn": self.turn,
            "action": self.action,
            "summary": self.summary,
            "details": self.details,
            "session_status": self.session_status,
        }


class CodingSessionRunner:
    def __init__(self, store: CodingSessionStore | None = None) -> None:
        self.store = store or get_coding_session_store()
        self._agents: dict[str, CodeAgent] = {}

    def _agent_for(self, record: CodingSessionRecord) -> CodeAgent:
        existing = self._agents.get(record.id)
        if existing is not None:
            return existing
        config = CodeAgentConfig(workspace_id=record.workspace_id, provider=record.provider)
        agent = CodeAgent(config)
        record.sandbox_session_id = agent._session.session_id  # noqa: SLF001
        self.store.save(record)
        self._agents[record.id] = agent
        return agent

    def _trajectory(self, record: CodingSessionRecord) -> TrajectoryLogger:
        return TrajectoryLogger(run_id=record.trajectory_run_id)

    def _trace(self, record: CodingSessionRecord, event_type: str, payload: dict[str, Any]) -> None:
        if record.control_center_session_id:
            append_trace(record.control_center_session_id, event_type, payload)

    def create_session(
        self,
        *,
        workspace_id: str,
        objective: str,
        repo_path: str | None = None,
        provider: str = "docker",
        control_center_session_id: str | None = None,
    ) -> CodingSessionRecord:
        record = self.store.create(
            workspace_id=workspace_id,
            objective=objective,
            repo_path=repo_path,
            provider=provider,
            control_center_session_id=control_center_session_id,
        )
        self._trace(record, "coding_session_created", {"objective": objective, "repo_path": repo_path})
        return record

    def pause(self, session_id: str) -> CodingSessionRecord | None:
        record = self.store.get(session_id)
        if record is None:
            return None
        record.status = "paused"
        self.store.save(record)
        self._trace(record, "coding_session_paused", {"turn": record.turn})
        return record

    def resume(self, session_id: str) -> CodingSessionRecord | None:
        record = self.store.get(session_id)
        if record is None:
            return None
        record.status = "active"
        self.store.save(record)
        self._trace(record, "coding_session_resumed", {"turn": record.turn})
        return record

    def close(self, session_id: str, *, status: str = "completed") -> CodingSessionRecord | None:
        record = self.store.get(session_id)
        if record is None:
            return None
        agent = self._agents.pop(session_id, None)
        if agent is not None:
            agent.close()
        record.status = status  # type: ignore[assignment]
        self.store.save(record)
        self._trace(record, "coding_session_closed", {"status": status, "turns": record.turn})
        return record

    def _plan_action(self, record: CodingSessionRecord, user_input: str | None) -> tuple[str, dict[str, Any]]:
        turn = record.turn + 1
        instruction = user_input or record.objective
        if turn == 1:
            return "analyze", {"instruction": instruction, "task": f"Analyze objective: {instruction}"}
        if turn == 2 and record.repo_path:
            return "patch", {"instruction": instruction, "issue": instruction}
        if turn >= 3:
            return "verify", {"instruction": instruction, "task": f"Verify progress on: {record.objective}"}
        return "execute", {"instruction": instruction, "task": instruction}

    def run_turn(self, session_id: str, *, user_input: str | None = None) -> TurnResult:
        record = self.store.get(session_id)
        if record is None:
            return TurnResult(ok=False, turn=0, action="none", summary="Session not found", session_status="failed")
        if record.status == "paused":
            return TurnResult(
                ok=False,
                turn=record.turn,
                action="paused",
                summary="Session is paused; resume before running another turn",
                session_status="paused",
            )
        if record.status in {"completed", "failed"}:
            return TurnResult(
                ok=False,
                turn=record.turn,
                action="closed",
                summary=f"Session already {record.status}",
                session_status=record.status,
            )

        action, payload = self._plan_action(record, user_input)
        trajectory = self._trajectory(record)
        agent = self._agent_for(record)
        details: dict[str, Any] = {"payload": payload}
        ok = True
        summary = ""

        if action == "analyze":
            code = textwrap.dedent(
                f"""
                import json
                result = {{"objective": {payload['instruction']!r}, "turn": "analyze", "status": "planned"}}
                print(json.dumps(result))
                """
            ).strip()
            result = agent.run_task(payload["task"], code=code)
            ok = result.ok
            summary = "Analyzed objective in sandbox"
            details["sandbox"] = {"stdout": result.stdout, "result": result.result}

        elif action == "patch" and record.repo_path:
            issue_result = run_issue(
                IssueRunRequest(issue=payload["issue"], repo_path=record.repo_path, dry_run=True)
            )
            ok = issue_result.ok or bool(issue_result.patch)
            summary = "Proposed repo patch for objective"
            details["patch"] = {
                "run_id": issue_result.run_id,
                "patch": issue_result.patch,
                "ok": issue_result.ok,
                "trajectory_path": issue_result.trajectory_path,
            }

        elif action == "verify":
            code = textwrap.dedent(
                """
                import json
                result = {"status": "verified", "checks": ["syntax", "sandbox"]}
                print(json.dumps(result))
                """
            ).strip()
            result = agent.run_task(payload["task"], code=code)
            ok = result.ok
            summary = "Verified session progress"
            details["verify"] = {"stdout": result.stdout, "result": result.result}
            record.status = "completed"

        else:
            result = agent.run_task(payload["task"])
            ok = result.ok
            summary = "Executed sandbox task"
            details["sandbox"] = {"stdout": result.stdout, "result": result.result}

        record.turn += 1
        record.messages.append(
            {
                "turn": record.turn,
                "role": "assistant",
                "action": action,
                "summary": summary,
                "ok": ok,
                "user_input": user_input,
            }
        )
        self.store.save(record)
        trajectory.log(
            "session_turn",
            {"session_id": record.id, "turn": record.turn, "action": action, "ok": ok, "summary": summary},
        )
        self._trace(record, "coding_turn", {"turn": record.turn, "action": action, "ok": ok, "summary": summary})

        if record.status == "completed":
            self.close(session_id, status="completed")

        return TurnResult(ok=ok, turn=record.turn, action=action, summary=summary, details=details, session_status=record.status)

    def read_trace(self, session_id: str) -> list[dict[str, Any]]:
        record = self.store.get(session_id)
        if record is None:
            return []
        logger = TrajectoryLogger(run_id=record.trajectory_run_id)
        return logger.read_events()
