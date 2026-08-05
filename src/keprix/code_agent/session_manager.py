"""
Long-horizon coding session manager.

Wraps CodeAgent to support multi-step sessions with:
  - Per-step transcript (task, code, stdout, errors)
  - Accumulated file-edit tracking
  - Checkpoint: serialise session state to disk
  - Resume: reload session from a checkpoint and continue

This fills the OpenHands-style long-horizon gap (Prompt 55 / 64 partial).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from keprix.compat import UTC
from pathlib import Path
from typing import Any

from keprix.code_agent.code_agent import CodeAgent, CodeAgentConfig, CodeAgentResult


@dataclass
class SessionStep:
    step_id: str
    step_number: int
    task: str
    code: str
    ok: bool
    stdout: str
    stderr: str
    result: Any
    errors: list[str]
    files_edited: list[str]
    needs_approval: bool
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "task": self.task,
            "code": self.code,
            "ok": self.ok,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "result": self.result,
            "errors": self.errors,
            "files_edited": self.files_edited,
            "needs_approval": self.needs_approval,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionStep:
        return cls(**data)


@dataclass
class SessionState:
    session_id: str
    workspace_id: str
    config: dict[str, Any]
    steps: list[dict[str, Any]] = field(default_factory=list)
    files_touched: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    closed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "workspace_id": self.workspace_id,
            "config": self.config,
            "steps": self.steps,
            "files_touched": self.files_touched,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "closed": self.closed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionState:
        return cls(**data)


def _default_checkpoint_dir() -> Path:
    import os

    base = Path(os.environ.get("KEPRIX_DATA_DIR", "/tmp/keprix-data"))
    path = base / "session-checkpoints"
    path.mkdir(parents=True, exist_ok=True)
    return path


class LongHorizonSession:
    """
    A persistent, multi-step coding session.

    Each call to run_step() appends a SessionStep to the transcript.
    Call checkpoint() at any point to save state. Call LongHorizonSession.resume()
    to continue from a saved checkpoint.
    """

    def __init__(
        self,
        *,
        session_id: str | None = None,
        workspace_id: str = "default",
        config: CodeAgentConfig | None = None,
        checkpoint_dir: Path | None = None,
        _state: SessionState | None = None,
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.workspace_id = workspace_id
        self.config = config or CodeAgentConfig(workspace_id=workspace_id)
        self.checkpoint_dir = checkpoint_dir or _default_checkpoint_dir()
        self._agent = CodeAgent(self.config)
        self._steps: list[SessionStep] = []
        self._files_touched: set[str] = set()

        if _state is not None:
            self._steps = [SessionStep.from_dict(s) for s in _state.steps]
            self._files_touched = set(_state.files_touched)

    def step_count(self) -> int:
        return len(self._steps)

    def run_step(
        self,
        task: str,
        *,
        code: str | None = None,
        files: list[str] | None = None,
    ) -> SessionStep:
        """
        Run one step in the session and record it in the transcript.

        files: optional list of file paths this step is expected to touch.
               Tracked in session-level files_touched set for resume awareness.
        """
        result: CodeAgentResult = self._agent.run_task(task, code=code)
        edited = list(files or [])
        for path in edited:
            self._files_touched.add(path)

        step = SessionStep(
            step_id=str(uuid.uuid4()),
            step_number=len(self._steps) + 1,
            task=task,
            code=result.code,
            ok=result.ok,
            stdout=result.stdout,
            stderr=result.stderr,
            result=result.result,
            errors=list(result.errors),
            files_edited=edited,
            needs_approval=result.needs_approval,
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._steps.append(step)
        return step

    def files_touched(self) -> list[str]:
        return sorted(self._files_touched)

    def transcript(self) -> str:
        """Human-readable summary of all steps."""
        lines: list[str] = [f"Session: {self.session_id}", f"Workspace: {self.workspace_id}", ""]
        for step in self._steps:
            status = "ok" if step.ok else "FAILED"
            lines.append(f"Step {step.step_number} [{status}] {step.timestamp}")
            lines.append(f"  Task: {step.task}")
            if step.stdout:
                lines.append(f"  Stdout: {step.stdout[:200]}")
            if step.errors:
                lines.append(f"  Errors: {'; '.join(step.errors[:3])}")
            if step.needs_approval:
                lines.append("  NOTE: needs_approval=True")
            lines.append("")
        return "\n".join(lines)

    def last_step(self) -> SessionStep | None:
        return self._steps[-1] if self._steps else None

    def failed_steps(self) -> list[SessionStep]:
        return [s for s in self._steps if not s.ok]

    def checkpoint(self) -> Path:
        """Serialise session state to disk and return the checkpoint file path."""
        state = SessionState(
            session_id=self.session_id,
            workspace_id=self.workspace_id,
            config={
                "provider": self.config.provider,
                "workspace_id": self.config.workspace_id,
                "approval_threshold": self.config.approval_threshold,
                "max_runtime_s": self.config.max_runtime_s,
                "memory_limit_mb": self.config.memory_limit_mb,
            },
            steps=[s.to_dict() for s in self._steps],
            files_touched=sorted(self._files_touched),
            last_updated=datetime.now(UTC).isoformat(),
        )
        path = self.checkpoint_dir / f"{self.session_id}.json"
        path.write_text(json.dumps(state.to_dict(), indent=2, default=str), encoding="utf-8")
        return path

    @classmethod
    def resume(
        cls,
        checkpoint_path: Path | str,
        *,
        checkpoint_dir: Path | None = None,
    ) -> LongHorizonSession:
        """Load a session from a checkpoint file and return a ready-to-use instance."""
        path = Path(checkpoint_path)
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        state = SessionState.from_dict(raw)
        config = CodeAgentConfig(
            workspace_id=state.config.get("workspace_id", state.workspace_id),
            provider=state.config.get("provider", "docker"),
            approval_threshold=state.config.get("approval_threshold", "medium"),
            max_runtime_s=state.config.get("max_runtime_s", 30),
            memory_limit_mb=state.config.get("memory_limit_mb", 256),
        )
        session = cls(
            session_id=state.session_id,
            workspace_id=state.workspace_id,
            config=config,
            checkpoint_dir=checkpoint_dir or path.parent,
            _state=state,
        )
        return session

    def close(self) -> None:
        self._agent.close()
