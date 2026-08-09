"""Human-in-the-loop validation gates between task chunks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from keprix.agent_state.context_state import ContextStateStore
from keprix.agent_state.models import (
    CheckpointGate,
    ErrorRecord,
    ProjectState,
    TaskChunk,
    utc_now_iso,
)

AutoCheckFn = Callable[[str, dict[str, Any]], dict[str, Any]]


class CheckpointBlockedError(RuntimeError):
    """Raised when work tries to advance past an unapproved checkpoint."""


class CheckpointValidator:
    """Pause after each chunk until an explicit human approval signal."""

    def __init__(
        self,
        store: ContextStateStore | None = None,
        *,
        auto_checks: list[AutoCheckFn] | None = None,
    ) -> None:
        self.store = store or ContextStateStore()
        self.auto_checks = list(auto_checks or [])

    def _chunk(self, state: ProjectState, chunk_id: str) -> TaskChunk:
        for chunk in state.chunks:
            if chunk.id == chunk_id:
                return chunk
        raise KeyError(f"Unknown chunk '{chunk_id}'")

    def start_chunk(self, session_id: str, chunk_id: str) -> ProjectState:
        state = self.store.require_state(session_id)
        self.assert_can_proceed(state)
        chunk = self._chunk(state, chunk_id)
        for dep in chunk.dependencies:
            dep_chunk = self._chunk(state, dep)
            if dep_chunk.status != "merged":
                raise RuntimeError(
                    f"Chunk '{chunk_id}' depends on '{dep}' which is {dep_chunk.status}"
                )

        self.store.save_checkpoint_snapshot(session_id, chunk_id)
        state = self.store.require_state(session_id)
        chunk = self._chunk(state, chunk_id)
        chunk.status = "in_progress"
        chunk.context_snapshot = self.store.load_checkpoint_snapshot(
            session_id, chunk_id
        ).to_dict()
        state.current_chunk_id = chunk_id

        first_step_id = None
        for step in state.pending:
            if step.chunk_id == chunk_id or step.id in set(chunk.steps):
                first_step_id = step.id
                break
        self.store.write_state(state)
        if first_step_id:
            return self.store.update_state_file(
                session_id, step_id=first_step_id, status="in_progress"
            )
        return self.store.require_state(session_id)

    def build_summary(self, state: ProjectState, chunk_id: str) -> dict[str, Any]:
        chunk = self._chunk(state, chunk_id)
        step_ids = set(chunk.steps)
        chunk_steps = [s for s in state.all_steps() if s.id in step_ids or s.chunk_id == chunk_id]
        completed = [s for s in chunk_steps if s.status == "completed"]
        failed = [s for s in chunk_steps if s.status in {"failed", "blocked"}]
        next_chunk = None
        for candidate in state.chunks:
            if candidate.id != chunk_id and candidate.status == "pending":
                next_chunk = {
                    "id": candidate.id,
                    "description": candidate.description,
                    "steps": list(candidate.steps),
                }
                break
        chunk_step_ids = {s.id for s in chunk_steps}
        errors = [e.to_dict() for e in state.errors if e.step_id in chunk_step_ids]
        if not errors:
            errors = [e.to_dict() for e in state.errors[-5:]]
        return {
            "chunk_id": chunk_id,
            "what_was_built": [s.description for s in completed],
            "files_changed": list(state.files_changed),
            "errors": errors,
            "failed_steps": [s.to_dict() for s in failed],
            "decisions_made": [d.to_dict() for d in state.decisions[-10:]],
            "next_chunk_preview": next_chunk,
            "step_outputs": [
                {"id": s.id, "description": s.description, "output": s.output}
                for s in completed
            ],
        }

    def pause_for_review(
        self,
        session_id: str,
        chunk_id: str,
        summary: str | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Present summary and block progress until human approval."""
        state = self.store.require_state(session_id)
        chunk = self._chunk(state, chunk_id)
        payload = summary if isinstance(summary, dict) else None
        if payload is None:
            payload = self.build_summary(state, chunk_id)
            if isinstance(summary, str) and summary.strip():
                payload["operator_notes"] = summary.strip()

        chunk.status = "awaiting_approval"
        chunk.summary = payload.get("operator_notes") or (
            f"Completed {len(payload.get('what_was_built') or [])} steps in {chunk_id}"
        )
        state.checkpoint = CheckpointGate(
            status="awaiting_approval",
            chunk_id=chunk_id,
            summary=chunk.summary,
            human_signal=None,
            updated_at=utc_now_iso(),
        )
        self.store.write_state(state)
        return {
            "status": "awaiting_approval",
            "chunk_id": chunk_id,
            "summary": payload,
            "can_proceed": False,
            "message": "HALT: human approval required before the next chunk",
        }

    def validate_chunk_output(
        self,
        session_id: str,
        chunk_id: str,
        output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run automated checks (lint/test hooks); default is a structural pass."""
        state = self.store.require_state(session_id)
        chunk = self._chunk(state, chunk_id)
        payload = dict(output or {})
        payload.setdefault("chunk_id", chunk_id)
        payload.setdefault("steps", list(chunk.steps))
        results: list[dict[str, Any]] = []
        ok = True
        if not self.auto_checks:
            unfinished = [
                s
                for s in state.all_steps()
                if s.id in set(chunk.steps) and s.status != "completed"
            ]
            check = {
                "name": "all_steps_completed",
                "ok": not unfinished,
                "unfinished": [s.id for s in unfinished],
            }
            results.append(check)
            ok = bool(check["ok"])
        for fn in self.auto_checks:
            result = dict(fn(chunk_id, payload) or {})
            results.append(result)
            if not result.get("ok", False):
                ok = False
        return {"ok": ok, "checks": results, "chunk_id": chunk_id}

    def approve(
        self,
        session_id: str,
        chunk_id: str,
        *,
        human_signal: str = "approved",
    ) -> ProjectState:
        state = self.store.require_state(session_id)
        chunk = self._chunk(state, chunk_id)
        if state.checkpoint.status != "awaiting_approval" or state.checkpoint.chunk_id != chunk_id:
            raise RuntimeError(
                f"Chunk '{chunk_id}' is not awaiting approval "
                f"(checkpoint={state.checkpoint.status})"
            )
        if not str(human_signal).strip():
            raise ValueError("human_signal is required for approval")
        chunk.status = "approved"
        state.checkpoint = CheckpointGate(
            status="approved",
            chunk_id=chunk_id,
            summary=chunk.summary,
            human_signal=str(human_signal).strip(),
            updated_at=utc_now_iso(),
        )
        return self.store.write_state(state)

    def reject(
        self,
        session_id: str,
        chunk_id: str,
        *,
        human_signal: str = "rejected",
        rollback: bool = True,
    ) -> ProjectState:
        state = self.store.require_state(session_id)
        chunk = self._chunk(state, chunk_id)
        chunk.status = "rejected"
        state.checkpoint = CheckpointGate(
            status="rejected",
            chunk_id=chunk_id,
            summary=chunk.summary,
            human_signal=str(human_signal).strip() or "rejected",
            updated_at=utc_now_iso(),
        )
        self.store.write_state(state)
        if rollback:
            return self.rollback_chunk(session_id, chunk_id)
        return self.store.require_state(session_id)

    def merge_approved_chunk(self, session_id: str, chunk_id: str) -> ProjectState:
        state = self.store.require_state(session_id)
        chunk = self._chunk(state, chunk_id)
        if chunk.status != "approved" and state.checkpoint.status != "approved":
            raise CheckpointBlockedError(
                "Cannot merge chunk without human approval signal"
            )
        if state.checkpoint.chunk_id != chunk_id or not state.checkpoint.human_signal:
            raise CheckpointBlockedError(
                "Agent cannot proceed past a checkpoint without human confirmation signal"
            )
        chunk.status = "merged"
        state.checkpoint = CheckpointGate(
            status="none",
            chunk_id=None,
            summary=None,
            human_signal=None,
            updated_at=utc_now_iso(),
        )
        state.current_chunk_id = None
        for candidate in state.chunks:
            if candidate.status == "pending":
                state.current_chunk_id = candidate.id
                break
        return self.store.write_state(state)

    def rollback_chunk(self, session_id: str, chunk_id: str) -> ProjectState:
        """Restore state to the snapshot taken at chunk start."""
        restored = self.store.restore_checkpoint_snapshot(session_id, chunk_id)
        for chunk in restored.chunks:
            if chunk.id == chunk_id:
                chunk.status = "failed"
        restored.checkpoint = CheckpointGate(status="none", updated_at=utc_now_iso())
        restored.errors.append(
            ErrorRecord(
                id=f"error-{uuid4().hex[:8]}",
                message=f"Chunk {chunk_id} rolled back after failure or rejection",
            )
        )
        return self.store.write_state(restored)

    def assert_can_proceed(self, state_or_session: ProjectState | str) -> None:
        if isinstance(state_or_session, str):
            state = self.store.require_state(state_or_session)
        else:
            state = state_or_session
        if state.checkpoint.status == "awaiting_approval":
            raise CheckpointBlockedError(
                f"Checkpoint awaiting human approval for chunk "
                f"{state.checkpoint.chunk_id}; cannot proceed"
            )
        if state.checkpoint.status == "rejected":
            raise CheckpointBlockedError(
                f"Checkpoint rejected for chunk {state.checkpoint.chunk_id}"
            )
