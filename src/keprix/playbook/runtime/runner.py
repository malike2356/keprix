"""Playbook execution engine."""

from __future__ import annotations

import time
import asyncio
from typing import Any
from uuid import uuid4

from keprix.playbook.runtime.checkpoint import CheckpointStore, make_checkpoint
from keprix.playbook.runtime.errors import (
    PlaybookCancelled,
    PlaybookInterrupt,
    PlaybookPaused,
    PlaybookRunError,
)
from keprix.playbook.runtime.event_payload import (
    build_node_completed_payload,
    build_node_failed_payload,
    build_node_started_payload,
)
from keprix.playbook.runtime.events import EventEmitter, EventType
from keprix.playbook.runtime.graph import END, CompiledPlaybookGraph
from keprix.playbook.runtime.interrupts import merge_state_patch
from keprix.playbook.runtime.state import PlaybookRun, RunStatus
from keprix.integrations.connector_audit import enrich_run_event
from keprix.integrations.scout_lifecycle_client import emit_scout_lifecycle_event
from keprix.playbook.run_telemetry import enrich_run_completion


class PlaybookRunner:
    """Executes compiled playbook graphs with checkpointing and interrupts."""

    def __init__(
        self,
        graph: CompiledPlaybookGraph,
        *,
        checkpoint_store: CheckpointStore | None = None,
        events: EventEmitter | None = None,
    ) -> None:
        self.graph = graph
        self.checkpoint_store = checkpoint_store
        self.events = events or EventEmitter()

    async def start(
        self,
        *,
        workspace_id: str,
        initial_state: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> PlaybookRun:
        run = PlaybookRun(
            run_id=run_id or str(uuid4()),
            graph_id=self.graph.graph_id,
            workspace_id=workspace_id,
            status=RunStatus.PENDING,
            state=dict(initial_state or {}),
        )
        self.events.emit(EventType.RUN_STARTED, run.run_id, graph_id=run.graph_id)
        return await self._execute(run)

    async def execute_inline(self, state: dict[str, Any]) -> PlaybookRun:
        run = PlaybookRun(
            run_id=str(uuid4()),
            graph_id=self.graph.graph_id,
            workspace_id="inline",
            status=RunStatus.RUNNING,
            state=dict(state),
        )
        return await self._execute(run, inline=True)

    async def resume(
        self,
        run: PlaybookRun,
        *,
        state_patch: dict[str, Any] | None = None,
        approved_by: str | None = None,
    ) -> PlaybookRun:
        if run.status not in {
            RunStatus.INTERRUPTED,
            RunStatus.WAITING_FOR_APPROVAL,
            RunStatus.PAUSED,
            RunStatus.FAILED,
        }:
            raise PlaybookRunError(f"Run {run.run_id} cannot resume from status {run.status.value}")

        run.state = merge_state_patch(run.state, state_patch)
        run.status = RunStatus.RUNNING
        run.error = None
        run.interrupt_reason = None
        run.approval_request = None
        self.events.emit(
            EventType.RESUMED,
            run.run_id,
            approved_by=approved_by,
            state_patch=state_patch or {},
        )
        return await self._execute(run, resume=True)

    async def _execute(
        self,
        run: PlaybookRun,
        *,
        inline: bool = False,
        resume: bool = False,
    ) -> PlaybookRun:
        del resume  # reserved for future step-level resume semantics
        run.status = RunStatus.RUNNING
        current = run.current_node or self.graph.entry

        while current and current != END:
            if run.status == RunStatus.CANCELLED:
                raise PlaybookCancelled(f"Run {run.run_id} cancelled")

            run.current_node = current
            node = self.graph.nodes[current]
            input_state = dict(run.state)
            started_at = time.perf_counter()

            self.events.emit(
                EventType.NODE_STARTED,
                run.run_id,
                **build_node_started_payload(node=current, input_state=input_state),
            )

            try:
                output_state = await node.invoke(run.state)
                run.state = output_state
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                await self._checkpoint(
                    run,
                    node_name=current,
                    input_state=input_state,
                    output_state=output_state,
                )
                self.events.emit(
                    EventType.NODE_COMPLETED,
                    run.run_id,
                    **enrich_run_event(
                        build_node_completed_payload(
                            node=current,
                            input_state=input_state,
                            output_state=output_state,
                            duration_ms=duration_ms,
                        ),
                        step_config=dict(node.metadata.get("config") or {}),
                    ),
                )
            except PlaybookInterrupt as exc:
                run.status = (
                    RunStatus.WAITING_FOR_APPROVAL
                    if exc.approval_request
                    else RunStatus.INTERRUPTED
                )
                run.interrupt_reason = exc.reason
                run.approval_request = exc.approval_request
                await self._checkpoint(
                    run,
                    node_name=current,
                    input_state=input_state,
                    output_state=None,
                    approval_request=exc.approval_request,
                )
                event_type = (
                    EventType.APPROVAL_REQUESTED
                    if exc.approval_request
                    else EventType.INTERRUPTED
                )
                self.events.emit(
                    event_type,
                    run.run_id,
                    node=current,
                    reason=exc.reason,
                    approval_request=exc.approval_request,
                )
                return run
            except PlaybookPaused:
                run.status = RunStatus.PAUSED
                self.events.emit(EventType.PAUSED, run.run_id, node=current)
                return run
            except PlaybookCancelled:
                run.status = RunStatus.CANCELLED
                self.events.emit(EventType.CANCELLED, run.run_id, node=current)
                raise
            except Exception as exc:
                run.status = RunStatus.FAILED
                run.error = str(exc)
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                await self._checkpoint(
                    run,
                    node_name=current,
                    input_state=input_state,
                    output_state=None,
                    error=str(exc),
                )
                self.events.emit(
                    EventType.NODE_FAILED,
                    run.run_id,
                    **build_node_failed_payload(
                        node=current,
                        input_state=input_state,
                        error=str(exc),
                        duration_ms=duration_ms,
                    ),
                )
                self._emit_terminal_telemetry(run)
                if inline:
                    raise
                return run

            next_node = self.graph.next_node(current, run.state)
            if next_node is None or next_node == END:
                break
            current = next_node

        run.status = RunStatus.COMPLETED
        run.current_node = None
        self.events.emit(EventType.COMPLETED, run.run_id, state=run.state)
        self._emit_terminal_telemetry(run)
        return run

    def _emit_terminal_telemetry(self, run: PlaybookRun) -> None:
        events = [event.to_dict() for event in self.events.list_events(run.run_id)]
        try:
            from keprix.agent_os.hooks import record_playbook_run_completion

            record_playbook_run_completion(run, events)
        except Exception:
            pass
        payload = enrich_run_completion(
            run,
            playbook_id=str(run.state.get("_playbook_id") or run.graph_id),
            version_hash=(
                str(run.state.get("_playbook_version_hash"))
                if run.state.get("_playbook_version_hash")
                else None
            ),
            events=events,
        )
        try:
            asyncio.create_task(
                emit_scout_lifecycle_event(
                    "playbook_run_completed",
                    payload,
                    workspace_id=run.workspace_id,
                )
            )
        except RuntimeError:
            pass

    async def _checkpoint(
        self,
        run: PlaybookRun,
        *,
        node_name: str,
        input_state: dict[str, Any],
        output_state: dict[str, Any] | None,
        error: str | None = None,
        approval_request: dict | None = None,
    ) -> None:
        if self.checkpoint_store is None:
            return
        record = make_checkpoint(
            run_id=run.run_id,
            graph_id=run.graph_id,
            node_name=node_name,
            input_state=input_state,
            output_state=output_state,
            error=error,
            approval_request=approval_request,
            artifacts=list(run.artifacts),
        )
        await self.checkpoint_store.save(record)


class PlaybookRunRegistry:
    """In-memory registry backing the playbook HTTP API."""

    def __init__(self) -> None:
        self._runs: dict[str, PlaybookRun] = {}
        self._runners: dict[str, PlaybookRunner] = {}
        self._events: dict[str, EventEmitter] = {}

    def register(self, run: PlaybookRun, runner: PlaybookRunner) -> None:
        self._runs[run.run_id] = run
        self._runners[run.run_id] = runner
        self._events[run.run_id] = runner.events

    def get(self, run_id: str) -> PlaybookRun | None:
        return self._runs.get(run_id)

    def get_runner(self, run_id: str) -> PlaybookRunner | None:
        return self._runners.get(run_id)

    def get_events(self, run_id: str) -> EventEmitter | None:
        return self._events.get(run_id)

    def list_runs(
        self,
        *,
        workspace_id: str | None = None,
        limit: int = 50,
    ) -> list[PlaybookRun]:
        """List in-memory runs (newest registration order first)."""
        runs = list(self._runs.values())
        if workspace_id:
            runs = [run for run in runs if run.workspace_id == workspace_id]
        runs.reverse()
        return runs[: max(1, min(limit, 200))]

    async def pause(self, run_id: str) -> PlaybookRun:
        run = self._require_run(run_id)
        if run.status not in {RunStatus.RUNNING, RunStatus.PENDING}:
            raise PlaybookRunError(f"Run {run_id} cannot be paused from status {run.status.value}")
        run.status = RunStatus.PAUSED
        emitter = self._events.get(run_id)
        if emitter:
            emitter.emit(EventType.PAUSED, run_id)
        return run

    async def cancel(self, run_id: str) -> PlaybookRun:
        run = self._require_run(run_id)
        if run.status in {RunStatus.COMPLETED, RunStatus.CANCELLED}:
            raise PlaybookRunError(f"Run {run_id} is already finished")
        run.status = RunStatus.CANCELLED
        emitter = self._events.get(run_id)
        if emitter:
            emitter.emit(EventType.CANCELLED, run_id)
        return run

    async def resume(
        self,
        run_id: str,
        *,
        state_patch: dict[str, Any] | None = None,
        approved_by: str | None = None,
    ) -> PlaybookRun:
        run = self._require_run(run_id)
        runner = self._require_runner(run_id)
        updated = await runner.resume(run, state_patch=state_patch, approved_by=approved_by)
        self._runs[run_id] = updated
        return updated

    def _require_run(self, run_id: str) -> PlaybookRun:
        run = self._runs.get(run_id)
        if run is None:
            raise PlaybookRunError(f"Run {run_id} not found")
        return run

    def _require_runner(self, run_id: str) -> PlaybookRunner:
        runner = self._runners.get(run_id)
        if runner is None:
            raise PlaybookRunError(f"Runner for {run_id} not found")
        return runner


playbook_registry = PlaybookRunRegistry()
