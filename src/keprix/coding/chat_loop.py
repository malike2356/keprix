"""Chat-to-edit loop combining context, patches, tests, and git proposals."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from keprix.coding.context_loader import LoadedContext, load_context, save_trace_bundle
from keprix.coding.git_workflow import GitCommitResult, auto_commit_after_tests, commit_changes, generate_commit_message, show_diff
from keprix.coding.issue_runner import IssueRunRequest, IssueRunResult, run_issue
from keprix.coding.lint_test_runner import detect_test_command, repair_loop, run_tests
from keprix.coding.repo_map import RepoMap, build_repo_map
from keprix.coding.trajectory import TrajectoryLogger
from keprix.coding.web_chat_export import WebChatBundle, export_web_chat_bundle


@dataclass
class CodingChatRequest:
    message: str
    repo_path: str | Path
    files: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    voice_transcript: str | None = None
    clipboard_text: str | None = None
    profile: str = "default"
    human_approved: bool = False
    auto_commit: bool = False
    commit_approved: bool = False


@dataclass
class CodingChatResult:
    ok: bool
    run_id: str
    issue_result: IssueRunResult | None
    repo_map: RepoMap | None
    context: LoadedContext | None
    diff: str
    commit: GitCommitResult | None
    test_summary: str
    export_bundle: WebChatBundle | None
    trajectory_path: str
    error: str | None = None


def run_coding_chat(request: CodingChatRequest) -> CodingChatResult:
    repo = Path(request.repo_path).resolve()
    logger = TrajectoryLogger()
    context = load_context(
        repo_path=repo,
        files=request.files,
        urls=request.urls,
        images=request.images,
        voice_transcript=request.voice_transcript,
        clipboard_text=request.clipboard_text,
        issue_text=request.message,
    )
    save_trace_bundle(context, logger.run_id)
    logger.log("context_loaded", context.to_trace_payload())

    repo_map = build_repo_map(repo)
    logger.log("repo_map", {"files": len(repo_map.files), "ignored": repo_map.ignored_count})

    issue_text = context.coding_request or request.message
    test_command = detect_test_command(repo)
    repair = repair_loop(repo, issue_text, test_command=test_command, max_attempts=2)
    issue_result = repair.runs[-1] if repair.runs else None
    test_summary = repair.last_test.output if repair.last_test else ""

    if issue_result is None:
        logger.log("error", {"message": "no issue run produced"})
        return CodingChatResult(
            ok=False,
            run_id=logger.run_id,
            issue_result=None,
            repo_map=repo_map,
            context=context,
            diff="",
            commit=None,
            test_summary=test_summary,
            export_bundle=None,
            trajectory_path=str(logger.path),
            error="issue run failed",
        )

    diff_result = show_diff(repo, issue_result.edits and [edit.path for edit in issue_result.edits if edit.ok] or None)
    commit_result: GitCommitResult | None = None
    changed_files = [edit.path for edit in issue_result.edits if edit.ok]
    if repair.ok and request.auto_commit:
        commit_result = auto_commit_after_tests(
            repo,
            issue=issue_text,
            files=changed_files,
            tests_passed=True,
            approved=request.commit_approved,
            enabled=True,
        )
    elif repair.ok and request.commit_approved and changed_files:
        commit_result = commit_changes(
            repo,
            message=generate_commit_message(repo, changed_files, issue_text),
            files=changed_files,
            approved=True,
            require_approval=True,
        )
    elif repair.ok and changed_files:
        commit_result = GitCommitResult(
            ok=False,
            message=generate_commit_message(repo, changed_files, issue_text),
            staged_files=changed_files,
            needs_approval=True,
            error="commit proposal awaiting approval",
        )

    export_bundle = export_web_chat_bundle(
        context=context,
        repo_map=repo_map,
        patch=issue_result.patch,
        test_summary=test_summary,
    )
    logger.log("chat_complete", {"ok": repair.ok, "commit_needs_approval": bool(commit_result and commit_result.needs_approval)})

    return CodingChatResult(
        ok=repair.ok and issue_result.ok,
        run_id=logger.run_id,
        issue_result=issue_result,
        repo_map=repo_map,
        context=context,
        diff=diff_result.diff,
        commit=commit_result,
        test_summary=test_summary,
        export_bundle=export_bundle,
        trajectory_path=str(logger.path),
        error=None if repair.ok else repair.error,
    )
