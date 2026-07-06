"""Coding agent HTTP routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.coding.chat_loop import CodingChatRequest, run_coding_chat
from keprix.coding.configs import list_profiles
from keprix.coding.context_loader import load_context
from keprix.coding.git_workflow import (
    commit_changes,
    create_branch,
    generate_commit_message,
    revert_keprix_changes,
    show_diff,
    stage_files,
)
from keprix.coding.issue_runner import IssueRunRequest, run_issue
from keprix.coding.lint_test_runner import detect_lint_command, detect_test_command, repair_loop, run_lint, run_tests
from keprix.coding.repo_map import build_repo_map
from keprix.coding.trajectory import TrajectoryLogger
from keprix.coding.voice_to_code import voice_to_coding_request
from keprix.coding.web_chat_export import export_web_chat_bundle
from keprix.public_api.auth import require_developer_session

router = APIRouter(prefix="/api/coding", tags=["coding"])


class RunBody(BaseModel):
    issue: str
    repo_path: str
    constraints: list[str] = Field(default_factory=list)
    test_command: str | None = None
    approval_policy: str = "default"
    profile: str = "default"
    human_approved: bool = False
    dry_run: bool = False


class ChatBody(BaseModel):
    message: str
    repo_path: str
    files: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    voice_transcript: str | None = None
    clipboard_text: str | None = None
    profile: str = "default"
    auto_commit: bool = False
    commit_approved: bool = False


class GitStageBody(BaseModel):
    repo_path: str
    files: list[str]


class GitCommitBody(BaseModel):
    repo_path: str
    message: str
    files: list[str] = Field(default_factory=list)
    approved: bool = False


class GitBranchBody(BaseModel):
    repo_path: str
    branch_name: str


class ContextBody(BaseModel):
    repo_path: str | None = None
    files: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    voice_transcript: str | None = None
    clipboard_text: str | None = None
    issue_text: str | None = None


class ExportBody(BaseModel):
    repo_path: str
    message: str
    files: list[str] = Field(default_factory=list)
    patch: str = ""
    test_summary: str = ""


def _repo(path: str) -> Path:
    repo = Path(path)
    if not repo.is_dir():
        raise HTTPException(status_code=400, detail="repo_path does not exist")
    return repo


@router.get("/profiles")
async def coding_profiles(_session: str = Depends(require_developer_session)) -> dict[str, Any]:
    return {"profiles": list_profiles()}


@router.post("/run")
async def coding_run(body: RunBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    repo = _repo(body.repo_path)
    result = run_issue(
        IssueRunRequest(
            issue=body.issue,
            repo_path=repo,
            constraints=body.constraints,
            test_command=body.test_command,
            approval_policy=body.approval_policy,
            profile=body.profile,
            human_approved=body.human_approved,
            dry_run=body.dry_run,
        )
    )
    return {
        "ok": result.ok,
        "run_id": result.run_id,
        "patch": result.patch,
        "explanation": result.explanation,
        "tests_run": result.tests_run,
        "test_summary": result.test_summary,
        "risk_notes": result.risk_notes,
        "trajectory_path": result.trajectory_path,
        "error": result.error,
    }


@router.post("/chat")
async def coding_chat(body: ChatBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    result = run_coding_chat(
        CodingChatRequest(
            message=body.message,
            repo_path=_repo(body.repo_path),
            files=body.files,
            urls=body.urls,
            images=body.images,
            voice_transcript=body.voice_transcript,
            clipboard_text=body.clipboard_text,
            profile=body.profile,
            auto_commit=body.auto_commit,
            commit_approved=body.commit_approved,
        )
    )
    return {
        "ok": result.ok,
        "run_id": result.run_id,
        "diff": result.diff,
        "patch": result.issue_result.patch if result.issue_result else "",
        "test_summary": result.test_summary,
        "commit": {
            "ok": result.commit.ok if result.commit else False,
            "message": result.commit.message if result.commit else "",
            "needs_approval": result.commit.needs_approval if result.commit else False,
            "commit_hash": result.commit.commit_hash if result.commit else None,
            "error": result.commit.error if result.commit else None,
        },
        "repo_map": result.repo_map.compact_text() if result.repo_map else "",
        "export_markdown": result.export_bundle.markdown if result.export_bundle else "",
        "trajectory_path": result.trajectory_path,
        "error": result.error,
    }


@router.get("/repo-map")
async def coding_repo_map(repo_path: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    repo_map = build_repo_map(_repo(repo_path))
    return {
        "root": repo_map.root,
        "files": repo_map.files,
        "routes": repo_map.routes,
        "tests": repo_map.tests,
        "recently_changed": repo_map.recently_changed,
        "ignored_count": repo_map.ignored_count,
        "compact": repo_map.compact_text(),
        "entries": {
            path: {
                "symbols": entry.symbols,
                "imports": entry.imports,
                "blame": [{"line_no": b.line_no, "author": b.author} for b in entry.blame],
            }
            for path, entry in repo_map.entries.items()
        },
    }


@router.get("/git/diff")
async def coding_git_diff(repo_path: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    result = show_diff(_repo(repo_path))
    return {"ok": result.ok, "diff": result.diff, "files": result.files, "error": result.error}


@router.post("/git/stage")
async def coding_git_stage(body: GitStageBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    result = stage_files(_repo(body.repo_path), body.files)
    return {"ok": result.ok, "diff": result.diff, "files": result.files, "error": result.error}


@router.post("/git/commit")
async def coding_git_commit(body: GitCommitBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    result = commit_changes(
        _repo(body.repo_path),
        message=body.message,
        files=body.files or None,
        approved=body.approved,
        require_approval=True,
    )
    return {
        "ok": result.ok,
        "commit_hash": result.commit_hash,
        "message": result.message,
        "staged_files": result.staged_files,
        "needs_approval": result.needs_approval,
        "error": result.error,
    }


@router.post("/git/branch")
async def coding_git_branch(body: GitBranchBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    result = create_branch(_repo(body.repo_path), body.branch_name)
    return {"ok": result.ok, "diff": result.diff, "error": result.error}


@router.post("/git/revert-keprix")
async def coding_git_revert(repo_path: str, approved: bool = False, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    result = revert_keprix_changes(_repo(repo_path), approved=approved, require_approval=True)
    return {
        "ok": result.ok,
        "reverted_files": result.reverted_files,
        "needs_approval": result.needs_approval,
        "error": result.error,
    }


@router.get("/lint-test/detect")
async def coding_detect_commands(repo_path: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    repo = _repo(repo_path)
    return {
        "test_command": detect_test_command(repo),
        "lint_command": detect_lint_command(repo),
    }


@router.post("/lint-test/run")
async def coding_lint_test_run(body: RunBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    repo = _repo(body.repo_path)
    result = repair_loop(repo, body.issue, test_command=body.test_command, max_attempts=3)
    return {
        "ok": result.ok,
        "attempts": result.attempts,
        "test_output": result.last_test.output if result.last_test else "",
        "lint_output": result.last_lint.output if result.last_lint else "",
        "error": result.error,
    }


@router.post("/context/load")
async def coding_context_load(body: ContextBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    repo = _repo(body.repo_path) if body.repo_path else None
    context = load_context(
        repo_path=repo,
        files=body.files,
        urls=body.urls,
        images=body.images,
        voice_transcript=body.voice_transcript,
        clipboard_text=body.clipboard_text,
        issue_text=body.issue_text,
    )
    return context.to_trace_payload() | {
        "artifacts": [
            {
                "kind": item.kind,
                "source": item.source,
                "summary": item.summary,
                "content_hash": item.content_hash,
                "preview": item.redacted_preview[:500],
            }
            for item in context.artifacts
        ]
    }


@router.post("/voice/normalize")
async def coding_voice_normalize(transcript: str, _session: str = Depends(require_developer_session)) -> dict[str, str]:
    return {"coding_request": voice_to_coding_request(transcript)}


@router.post("/export/web-chat")
async def coding_export_web_chat(body: ExportBody, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    repo = _repo(body.repo_path)
    context = load_context(repo_path=repo, files=body.files, issue_text=body.message)
    bundle = export_web_chat_bundle(
        context=context,
        repo_map=build_repo_map(repo),
        patch=body.patch,
        test_summary=body.test_summary,
    )
    return {"title": bundle.title, "markdown": bundle.markdown, "summary": bundle.json_summary}


@router.get("/trajectories/{run_id}")
async def coding_trajectory(run_id: str, _session: str = Depends(require_developer_session)) -> dict[str, Any]:
    logger = TrajectoryLogger(run_id=run_id)
    if logger.path is None or not logger.path.exists():
        raise HTTPException(status_code=404, detail="trajectory not found")
    return {"run_id": run_id, "events": logger.read_events()}
