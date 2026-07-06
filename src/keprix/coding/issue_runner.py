"""Issue-to-patch runner orchestrating filemap, edits, tests, and trajectory."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from keprix.coding.configs import CodingProfile, load_profile
from keprix.coding.filemap import RepoFilemap, build_filemap
from keprix.coding.parsers import ParsedIssue, extract_replacement_text, extract_target_file, parse_issue_input
from keprix.coding.patcher import PatchBundle, apply_patch_bundle, format_patch, rollback_patch
from keprix.coding.review import review_file_edit, review_run
from keprix.coding.scoped_replace import EditResult, append_to_file, create_file, replace_exact_block
from keprix.coding.trajectory import TrajectoryLogger


@dataclass
class IssueRunRequest:
    issue: str
    repo_path: str | Path
    constraints: list[str] = field(default_factory=list)
    test_command: str | None = None
    approval_policy: str = "default"
    profile: str = "default"
    human_approved: bool = False
    dry_run: bool = False


@dataclass
class IssueRunResult:
    run_id: str
    patch: str
    explanation: str
    tests_run: bool
    test_summary: str
    risk_notes: list[str]
    trajectory_path: str
    edits: list[EditResult] = field(default_factory=list)
    filemap: RepoFilemap | None = None
    ok: bool = True
    error: str | None = None


def run_issue(request: IssueRunRequest) -> IssueRunResult:
    repo_root = Path(request.repo_path).resolve()
    profile = load_profile(request.profile)
    logger = TrajectoryLogger()
    parsed = parse_issue_input(request.issue)
    risk_notes: list[str] = []

    logger.log("issue_parsed", {"title": parsed.title, "source": parsed.source})

    filemap = build_filemap(repo_root) if profile.use_filemap else None
    if filemap:
        logger.log("filemap_built", {"packages": len(filemap.packages), "tests": len(filemap.tests)})

    edits = _propose_edits(parsed, repo_root, filemap, profile, risk_notes)
    for edit in edits:
        decision = review_file_edit(edit.path, repo_root)
        if not decision.allowed:
            return _fail(logger, f"Edit blocked: {decision.reason}")

    run_decision = review_run(profile, edits_count=len(edits), human_approved=request.human_approved)
    if not run_decision.allowed:
        if run_decision.needs_approval:
            risk_notes.append(run_decision.reason)
            return IssueRunResult(
                run_id=logger.run_id,
                patch=format_patch(edits),
                explanation=_explain(parsed, edits),
                tests_run=False,
                test_summary="",
                risk_notes=risk_notes,
                trajectory_path=str(logger.path),
                edits=edits,
                filemap=filemap,
                ok=False,
                error=run_decision.reason,
            )
        return _fail(logger, run_decision.reason)

    bundle = PatchBundle(patch_text=format_patch(edits), edits=edits, explanation=_explain(parsed, edits))
    logger.log("patch_proposed", {"patch": bundle.patch_text, "edit_count": len(edits)})

    if request.dry_run:
        return IssueRunResult(
            run_id=logger.run_id,
            patch=bundle.patch_text,
            explanation=bundle.explanation,
            tests_run=False,
            test_summary="dry run",
            risk_notes=risk_notes,
            trajectory_path=str(logger.path),
            edits=edits,
            filemap=filemap,
        )

    applied = apply_patch_bundle(repo_root, bundle)
    logger.log("patch_applied", {"paths": [edit.path for edit in applied]})

    tests_run = False
    test_summary = ""
    if request.test_command and profile.allow_bash:
        tests_run = True
        test_summary, passed = _run_tests(request.test_command, repo_root)
        logger.log("tests_run", {"command": request.test_command, "summary": test_summary, "passed": passed})
        if not passed:
            rollback_patch(repo_root, applied)
            logger.log("rollback", {"reason": "tests failed"})
            return IssueRunResult(
                run_id=logger.run_id,
                patch=bundle.patch_text,
                explanation=bundle.explanation,
                tests_run=True,
                test_summary=test_summary,
                risk_notes=risk_notes + ["rolled back after test failure"],
                trajectory_path=str(logger.path),
                edits=applied,
                filemap=filemap,
                ok=False,
                error="tests failed; changes rolled back",
            )

    return IssueRunResult(
        run_id=logger.run_id,
        patch=bundle.patch_text,
        explanation=bundle.explanation,
        tests_run=tests_run,
        test_summary=test_summary,
        risk_notes=risk_notes,
        trajectory_path=str(logger.path),
        edits=applied,
        filemap=filemap,
    )


def _propose_edits(
    parsed: ParsedIssue,
    repo_root: Path,
    filemap: RepoFilemap | None,
    profile: CodingProfile,
    risk_notes: list[str],
) -> list[EditResult]:
    edits: list[EditResult] = []
    target = extract_target_file(parsed)
    replacement = extract_replacement_text(parsed)

    if target:
        path = repo_root / target
        if path.exists():
            body_lower = parsed.body.lower()
            if "replace" in body_lower and replacement is not None:
                import re

                match = re.search(r"replace\s+['\"](.+?)['\"]\s+with\s+['\"](.+?)['\"]", parsed.body, re.I)
                if match:
                    old_block = match.group(1)
                    new_block = match.group(2)
                    edits.append(replace_exact_block(repo_root, target, old_block, new_block))
                    return edits
            if replacement:
                edits.append(append_to_file(repo_root, target, replacement))
                return edits

    marker_name = "marker.txt"
    if filemap and filemap.tests:
        marker_name = filemap.tests[0]
    elif (repo_root / "README.md").exists():
        marker_name = "README.md"

    if (repo_root / marker_name).exists():
        edits.append(append_to_file(repo_root, marker_name, "\n# Keprix issue fix\n"))
    else:
        edits.append(create_file(repo_root, "KEPRIX_FIX.md", "# Issue fix\n\n" + parsed.title + "\n"))

    if profile.require_human_review:
        risk_notes.append("profile requires human review before apply")
    return edits


def _explain(parsed: ParsedIssue, edits: list[EditResult]) -> str:
  paths = ", ".join(edit.path for edit in edits if edit.ok) or "none"
  return f"Address issue '{parsed.title}' with edits to: {paths}"


def _run_tests(command: str, repo_root: Path) -> tuple[str, bool]:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=120,
        )
        summary = (proc.stdout or "") + (proc.stderr or "")
        return summary[:4000], proc.returncode == 0
    except Exception as exc:
        return str(exc), False


def _fail(logger: TrajectoryLogger, error: str) -> IssueRunResult:
    logger.log("error", {"message": error})
    return IssueRunResult(
        run_id=logger.run_id,
        patch="",
        explanation="",
        tests_run=False,
        test_summary="",
        risk_notes=[],
        trajectory_path=str(logger.path),
        ok=False,
        error=error,
    )
