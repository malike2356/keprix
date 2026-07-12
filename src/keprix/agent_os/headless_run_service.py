"""Headless Action Board runners for skills, playbooks, and Agent Apps."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from keprix.agent_apps.registry import get_agent_app_registry
from keprix.agent_apps.web_runner import run_web
from keprix.agent_os.hooks import record_external_run
from keprix.agent_os.run_ledger_store import RunLedgerStore
from keprix.playbook.runtime import PlaybookRunner, playbook_registry
from keprix.playbook.yaml_compiler import compile_playbook_document
from keprix_constants import get_keprix_home


@dataclass
class HeadlessRunResult:
    run_id: str
    source_type: str
    source_id: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    ledger_entry_id: str | None = None
    tokens: int = 0
    duration_ms: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "ledger_entry_id": self.ledger_entry_id,
            "tokens": self.tokens,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at,
            "events": self.events,
        }


def _runs_dir() -> Path:
    path = get_keprix_home() / "agent-os" / "headless-runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


class HeadlessRunService:
    def status(self, run_id: str) -> HeadlessRunResult | None:
        path = _runs_dir() / f"{run_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return HeadlessRunResult(**data)

    async def run_skill(self, slug: str, params: dict[str, Any] | None = None) -> HeadlessRunResult:
        skill_path = get_keprix_home() / "skills" / slug / "SKILL.md"
        if not skill_path.is_file():
            raise FileNotFoundError(f"Skill not found: {slug}")
        run_id = f"hrun_{uuid4().hex}"
        started = time.perf_counter()
        result = HeadlessRunResult(run_id=run_id, source_type="skill", source_id=slug, status="running")
        self._event(result, "queued", {"params": params or {}})
        self._save(result)
        try:
            text = skill_path.read_text(encoding="utf-8")
            output = {"summary": f"Loaded skill {slug}", "skill_bytes": len(text), "params": params or {}}
            result.status = "completed"
            result.output = output
            result.tokens = len(text.split())
            result.duration_ms = int((time.perf_counter() - started) * 1000)
            entry = record_external_run(
                source_type="skill",
                source_id=slug,
                run_id=run_id,
                workspace_id=str((params or {}).get("workspace_id") or "default"),
                status=result.status,
                input_summary=params or {},
                output_summary=output,
                tokens=result.tokens,
                duration_ms=result.duration_ms,
            )
            result.ledger_entry_id = entry.entry_id
            self._event(result, "completed", {"ledger_entry_id": entry.entry_id})
        except Exception as exc:
            self._fail(result, exc, started, params or {})
        self._save(result)
        return result

    async def run_playbook(self, playbook_id: str, inputs: dict[str, Any] | None = None) -> HeadlessRunResult:
        path = get_keprix_home() / "playbooks" / "promoted" / f"{playbook_id}.yaml"
        if not path.is_file():
            raise FileNotFoundError(f"Playbook not found: {playbook_id}")
        run_id = f"hrun_{uuid4().hex}"
        started = time.perf_counter()
        result = HeadlessRunResult(run_id=run_id, source_type="playbook", source_id=playbook_id, status="running")
        self._event(result, "queued", {"inputs": inputs or {}})
        self._save(result)
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            graph = compile_playbook_document(document).compile()
            runner = PlaybookRunner(graph)
            state = dict(inputs or {})
            state["_playbook_id"] = playbook_id
            run = await runner.start(workspace_id=str(state.get("workspace_id") or "default"), initial_state=state)
            playbook_registry.register(run, runner)
            entry = RunLedgerStore().get_by_run(run.run_id)
            result.status = run.status.value
            result.output = run.to_dict()
            result.duration_ms = int((time.perf_counter() - started) * 1000)
            result.ledger_entry_id = entry.entry_id if entry else None
            self._event(result, "completed", {"playbook_run_id": run.run_id, "ledger_entry_id": result.ledger_entry_id})
        except Exception as exc:
            self._fail(result, exc, started, inputs or {})
        self._save(result)
        return result

    async def run_agent_app(self, name: str, inputs: dict[str, Any] | None = None) -> HeadlessRunResult:
        app_dir = get_agent_app_registry().app_dir(name) or (get_keprix_home() / "agent-apps" / name)
        if not app_dir or not (Path(app_dir) / "agent.yaml").is_file():
            raise FileNotFoundError(f"Agent App not found: {name}")
        run_id = f"hrun_{uuid4().hex}"
        started = time.perf_counter()
        result = HeadlessRunResult(run_id=run_id, source_type="agent_app", source_id=name, status="running")
        self._event(result, "queued", {"inputs": inputs or {}})
        self._save(result)
        try:
            output = await asyncio.to_thread(run_web, Path(app_dir), input_text=str((inputs or {}).get("input") or ""), context={"form": inputs or {}})
            duration_ms = int((time.perf_counter() - started) * 1000)
            entry = record_external_run(
                source_type="agent_app",
                source_id=name,
                run_id=str(output.get("trace_id") or run_id),
                workspace_id=str((inputs or {}).get("workspace_id") or "default"),
                status="completed",
                input_summary=inputs or {},
                output_summary=output,
                duration_ms=duration_ms,
            )
            result.status = "completed"
            result.output = output
            result.duration_ms = duration_ms
            result.ledger_entry_id = entry.entry_id
            self._event(result, "completed", {"trace_id": output.get("trace_id"), "ledger_entry_id": entry.entry_id})
        except Exception as exc:
            self._fail(result, exc, started, inputs or {})
        self._save(result)
        return result

    def _event(self, result: HeadlessRunResult, event: str, payload: dict[str, Any]) -> None:
        result.events.append({"event": event, "payload": payload, "created_at": datetime.now(timezone.utc).isoformat()})

    def _fail(self, result: HeadlessRunResult, exc: Exception, started: float, input_summary: dict[str, Any]) -> None:
        result.status = "failed"
        result.error = str(exc)
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        entry = record_external_run(
            source_type=result.source_type,
            source_id=result.source_id,
            run_id=result.run_id,
            workspace_id=str(input_summary.get("workspace_id") or "default"),
            status="failed",
            input_summary=input_summary,
            output_summary={"error": str(exc)},
            duration_ms=result.duration_ms,
        )
        result.ledger_entry_id = entry.entry_id
        self._event(result, "failed", {"error": str(exc), "ledger_entry_id": entry.entry_id})

    def _save(self, result: HeadlessRunResult) -> None:
        (_runs_dir() / f"{result.run_id}.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
