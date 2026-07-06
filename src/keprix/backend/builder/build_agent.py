"""Build job orchestration (Prompt 29)."""

from __future__ import annotations

import asyncio
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.backend.builder.registry import get_project_registry
from keprix.backend.builder.stack_detector import detect_stack
from keprix.backend.builder.store import get_builder_store
from keprix.coding.git_workflow import show_diff
from keprix.coding.issue_runner import IssueRunRequest, run_issue
from keprix.coding.lint_test_runner import detect_test_command, run_tests


_running_jobs: set[str] = set()
_cancelled_jobs: set[str] = set()


def cancel_build_job(job_id: str) -> bool:
    _cancelled_jobs.add(job_id)
    store = get_builder_store()
    job = store.get_job(job_id)
    if job and job.get("status") == "running":
        store.update_job(job_id, {"status": "cancelled", "completed_at": _now()})
        store.append_job_log(job_id, "[builder] job cancelled")
        return True
    if job and job.get("status") == "pending":
        store.update_job(job_id, {"status": "cancelled", "completed_at": _now()})
        return True
    return False


def start_build_job(job_id: str) -> None:
    if job_id in _running_jobs:
        return
    thread = threading.Thread(target=_run_build_job, args=(job_id,), daemon=True)
    thread.start()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(job_id: str, message: str) -> None:
    get_builder_store().append_job_log(job_id, message)


def _run_build_job(job_id: str) -> None:
    store = get_builder_store()
    job = store.get_job(job_id)
    if job is None:
        return
    if job_id in _cancelled_jobs:
        return

    _running_jobs.add(job_id)
    store.update_job(job_id, {"status": "running", "started_at": _now()})
    project = store.get_project(str(job.get("project_id") or ""))
    if project is None:
        store.update_job(job_id, {"status": "failed", "completed_at": _now(), "output": "project not found"})
        _running_jobs.discard(job_id)
        return

    path = Path(project["path"])
    report = detect_stack(path)
    instruction = str(job.get("instruction") or "")
    _log(job_id, f"[builder] project={project['name']} stack={report.stack_type}")
    _log(job_id, f"[builder] instruction: {instruction}")

    if job_id in _cancelled_jobs:
        _running_jobs.discard(job_id)
        return

    try:
        result = run_issue(
            IssueRunRequest(
                issue=instruction,
                repo_path=path,
                constraints=[
                    f"Tech stack: {report.stack_type}",
                    f"Project path: {path}",
                    f"Completeness: {report.estimated_completeness}%",
                    "Follow existing project conventions.",
                ],
                dry_run=False,
            )
        )
        _log(job_id, f"[builder] patch applied: {bool(result.edits)}")
        if result.explanation:
            _log(job_id, result.explanation)
        if result.patch:
            _log(job_id, result.patch[:8000])

        test_cmd = detect_test_command(path)
        if test_cmd:
            _log(job_id, f"[builder] running tests: {test_cmd}")
            test_result = run_tests(path, test_cmd)
            _log(job_id, test_result.output)

        diff = show_diff(path)
        diff_summary = diff.diff[:8000] if diff.ok else (diff.error or "")
        needs_approval = (not result.ok and bool(result.patch)) or any(
            "review" in note.lower() or "blocked" in note.lower() for note in result.risk_notes
        )
        if needs_approval:
            from keprix.coding.trajectory_steps import append_trajectory_event

            append_trajectory_event(
                result.run_id,
                "approval_required",
                {
                    "reason": result.error or "Patch requires Tier 3 approval",
                    "patch": result.patch[:8000] if result.patch else "",
                    "needs_approval": True,
                },
            )

        status = "done" if result.ok else "failed"
        store.update_job(
            job_id,
            {
                "status": status,
                "completed_at": _now(),
                "diff_summary": diff_summary,
                "trajectory_run_id": result.run_id,
                "needs_tier3_approval": needs_approval,
                "approval_reason": result.error or "",
                "plan": {"steps": ["analyse", "patch", "test"]},
                "output": store.read_job_log(job_id),
            },
        )
        store.upsert_project({**project, "last_built_at": _now(), "build_log": store.read_job_log(job_id)})
    except Exception as exc:
        _log(job_id, f"[builder] error: {exc}")
        store.update_job(job_id, {"status": "failed", "completed_at": _now()})
    finally:
        _running_jobs.discard(job_id)


async def stream_job_log(job_id: str) -> Any:
    store = get_builder_store()
    last_len = 0
    while True:
        log_text = store.read_job_log(job_id)
        if len(log_text) > last_len:
            chunk = log_text[last_len:]
            last_len = len(log_text)
            for line in chunk.splitlines():
                yield {"type": "log", "line": line}
        job = store.get_job(job_id)
        if job and job.get("status") in {"done", "failed", "cancelled"}:
            yield {"type": "status", "status": job.get("status"), "diff_summary": job.get("diff_summary")}
            break
        await asyncio.sleep(0.4)


def git_project_status(project_path: str | Path) -> dict[str, Any]:
    path = Path(project_path)
    if not (path / ".git").exists():
        return {"has_git": False}
    try:
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=str(path), text=True).strip()
        status = subprocess.check_output(["git", "status", "--short"], cwd=str(path), text=True).strip()
        log = subprocess.check_output(["git", "log", "-5", "--oneline"], cwd=str(path), text=True).strip()
        return {"has_git": True, "branch": branch, "status": status, "recent_commits": log}
    except Exception as exc:
        return {"has_git": True, "error": str(exc)}
