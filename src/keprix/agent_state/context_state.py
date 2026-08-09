"""Running project state file manager (atomic JSON on disk)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.agent_state.models import (
    ConstraintRecord,
    DecisionRecord,
    ErrorRecord,
    ProjectState,
    StepRecord,
    utc_now_iso,
)
from keprix.utils import atomic_json_write


_SESSION_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def default_state_root() -> Path:
    override = (os.environ.get("KEPRIX_AGENT_STATE_DIR") or "").strip()
    if override:
        return Path(override).expanduser()
    home = Path(os.environ.get("KEPRIX_HOME") or Path.home() / ".keprix")
    return Path(home).expanduser() / "agent-state"


def sanitize_session_id(session_id: str) -> str:
    cleaned = _SESSION_SAFE.sub("_", (session_id or "").strip())
    return cleaned or "default"


class ContextStateStore:
    """Create, update, and resume durable agent project state files."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else default_state_root()
        self.root.mkdir(parents=True, exist_ok=True)

    def session_dir(self, session_id: str) -> Path:
        path = self.root / sanitize_session_id(session_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def state_path(self, session_id: str) -> Path:
        return self.session_dir(session_id) / "state.json"

    def checkpoint_dir(self, session_id: str) -> Path:
        path = self.session_dir(session_id) / "checkpoints"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def create_state_file(
        self,
        session_id: str,
        task_description: str,
        *,
        steps: list[str] | None = None,
        constraints: list[str] | None = None,
        decisions: list[str] | None = None,
    ) -> ProjectState:
        """Initialize state with optional seed steps, constraints, and decisions."""
        pending: list[StepRecord] = []
        for index, description in enumerate(steps or [], start=1):
            pending.append(
                StepRecord(
                    id=f"step-{index:03d}",
                    description=str(description).strip() or f"Step {index}",
                    status="pending",
                )
            )
        state = ProjectState(
            session_id=sanitize_session_id(session_id),
            task_description=(task_description or "").strip() or "Untitled task",
            pending=pending,
            constraints=[
                ConstraintRecord(id=f"constraint-{i}", text=str(text).strip())
                for i, text in enumerate(constraints or [], start=1)
                if str(text).strip()
            ],
            decisions=[
                DecisionRecord(id=f"decision-{i}", text=str(text).strip())
                for i, text in enumerate(decisions or [], start=1)
                if str(text).strip()
            ],
        )
        self.write_state(state)
        return state

    def write_state(self, state: ProjectState) -> ProjectState:
        state.updated_at = utc_now_iso()
        atomic_json_write(self.state_path(state.session_id), state.to_dict())
        return state

    def read_state_file(self, session_id: str) -> ProjectState | None:
        path = self.state_path(session_id)
        if not path.is_file():
            return None
        import json

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Corrupt agent state at {path}: expected object")
        return ProjectState.from_dict(data)

    def require_state(self, session_id: str) -> ProjectState:
        state = self.read_state_file(session_id)
        if state is None:
            raise FileNotFoundError(
                f"No agent state for session '{sanitize_session_id(session_id)}'"
            )
        return state

    def resume(self, session_id: str) -> dict[str, Any]:
        """Return resume payload: last completed step and next actionable step."""
        state = self.require_state(session_id)
        nxt = state.next_pending_step()
        gate = state.checkpoint
        return {
            "session_id": state.session_id,
            "task_description": state.task_description,
            "last_completed_step_id": state.last_completed_step_id,
            "next_step": nxt.to_dict() if nxt else None,
            "checkpoint": gate.to_dict(),
            "can_proceed": gate.status in {"none", "approved"},
            "completed_count": len(state.completed),
            "pending_count": len(state.pending),
            "in_progress_count": len(state.in_progress),
            "current_chunk_id": state.current_chunk_id,
            "state": state.to_dict(),
        }

    def format_for_injection(self, session_id: str) -> str | None:
        """Compact resume block for session-start / compression injection."""
        state = self.read_state_file(session_id)
        if state is None:
            return None
        nxt = state.next_pending_step()
        lines = [
            "[Agent project state resume]",
            f"Task: {state.task_description}",
            f"Completed: {len(state.completed)}; "
            f"in progress: {len(state.in_progress)}; "
            f"pending: {len(state.pending)}",
        ]
        if state.last_completed_step_id:
            lines.append(f"Last completed: {state.last_completed_step_id}")
        if nxt:
            lines.append(f"Resume at: {nxt.id} — {nxt.description} ({nxt.status})")
        if state.checkpoint.status == "awaiting_approval":
            lines.append(
                f"HALT: checkpoint awaiting human approval "
                f"(chunk {state.checkpoint.chunk_id})"
            )
        elif state.checkpoint.status == "approved" and state.current_chunk_id:
            lines.append(f"Checkpoint approved for chunk {state.checkpoint.chunk_id}")
        if state.decisions:
            lines.append("Recent decisions:")
            for decision in state.decisions[-3:]:
                lines.append(f"- {decision.text}")
        if state.constraints:
            lines.append("Constraints:")
            for constraint in state.constraints[-3:]:
                lines.append(f"- {constraint.text}")
        return "\n".join(lines)

    def update_state_file(
        self,
        session_id: str,
        *,
        step_id: str | None = None,
        status: str | None = None,
        output: str | None = None,
        description: str | None = None,
        decision: str | None = None,
        constraint: str | None = None,
        error: str | None = None,
        files_changed: list[str] | None = None,
    ) -> ProjectState:
        """Append/update after an agent step; auto-timestamps via write_state."""
        state = self.require_state(session_id)

        if decision and str(decision).strip():
            state.decisions.append(
                DecisionRecord(id=f"decision-{uuid4().hex[:8]}", text=str(decision).strip())
            )
        if constraint and str(constraint).strip():
            state.constraints.append(
                ConstraintRecord(
                    id=f"constraint-{uuid4().hex[:8]}", text=str(constraint).strip()
                )
            )
        if error and str(error).strip():
            state.errors.append(
                ErrorRecord(
                    id=f"error-{uuid4().hex[:8]}",
                    message=str(error).strip(),
                    step_id=step_id,
                )
            )
        if files_changed:
            for path in files_changed:
                text = str(path).strip()
                if text and text not in state.files_changed:
                    state.files_changed.append(text)

        if step_id:
            self._move_step(
                state,
                step_id=step_id,
                status=status or "in_progress",
                output=output,
                description=description,
            )

        return self.write_state(state)

    def _move_step(
        self,
        state: ProjectState,
        *,
        step_id: str,
        status: str,
        output: str | None,
        description: str | None,
    ) -> None:
        buckets = {
            "completed": state.completed,
            "in_progress": state.in_progress,
            "pending": state.pending,
            "blocked": state.blocked,
            "failed": state.blocked,  # failed tracked in blocked + errors
        }
        step: StepRecord | None = None
        for bucket in (state.completed, state.in_progress, state.pending, state.blocked):
            for index, item in enumerate(bucket):
                if item.id == step_id:
                    step = bucket.pop(index)
                    break
            if step is not None:
                break

        if step is None:
            step = StepRecord(
                id=step_id,
                description=description or step_id,
                status="pending",
            )

        if description:
            step.description = description
        if output is not None:
            step.output = output
        normalized = status if status in buckets else "pending"
        if normalized == "failed":
            step.status = "failed"
            state.blocked.append(step)
            state.errors.append(
                ErrorRecord(
                    id=f"error-{uuid4().hex[:8]}",
                    message=output or "Step failed",
                    step_id=step_id,
                )
            )
        else:
            step.status = normalized  # type: ignore[assignment]
            step.updated_at = utc_now_iso()
            buckets[normalized].append(step)
            if normalized == "completed":
                state.last_completed_step_id = step.id

    def save_checkpoint_snapshot(self, session_id: str, chunk_id: str) -> Path:
        state = self.require_state(session_id)
        path = self.checkpoint_dir(session_id) / f"{chunk_id}.json"
        atomic_json_write(path, state.snapshot())
        return path

    def load_checkpoint_snapshot(self, session_id: str, chunk_id: str) -> ProjectState:
        import json

        path = self.checkpoint_dir(session_id) / f"{chunk_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"No checkpoint snapshot for chunk '{chunk_id}'")
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return ProjectState.from_dict(data)

    def restore_checkpoint_snapshot(self, session_id: str, chunk_id: str) -> ProjectState:
        restored = self.load_checkpoint_snapshot(session_id, chunk_id)
        # Keep session id identity; mark rollback in errors
        restored.session_id = sanitize_session_id(session_id)
        restored.errors.append(
            ErrorRecord(
                id=f"error-{uuid4().hex[:8]}",
                message=f"Rolled back to checkpoint {chunk_id}",
                step_id=None,
            )
        )
        return self.write_state(restored)
