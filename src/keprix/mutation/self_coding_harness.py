"""Scoped self-coding mutation harness (Prompt 153)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from keprix.coding.git_workflow import show_diff
from keprix.coding.lint_test_runner import run_tests
from keprix.coding.scoped_replace import create_file
from keprix.mutation.config import get_mutation_settings
from keprix.mutation.self_coding_git import create_branch, current_branch, delete_branch
from keprix.mutation.self_coding_scope import (
    get_allowed_repo_root_relative_paths,
    is_allowed_target_dir,
    is_path_in_mutation_scope,
    validate_diff_scope,
)
from keprix.mutation.store import MutationStore

logger = logging.getLogger(__name__)

CodingRunner = Callable[
    [Path, "SelfCodingRequest", list[str]],
    tuple[str, list[str], str | None],
]


@dataclass
class SelfCodingRequest:
    task: str
    target_dir: str
    workspace_id: str
    requested_by: str
    run_tests: bool = True
    branch_name: str | None = None


@dataclass
class SelfCodingResult:
    success: bool
    mutation_id: str | None
    branch_name: str
    diff: str | None
    test_output: str | None
    test_passed: bool
    scope_valid: bool
    error: str | None
    files_changed: list[str] = field(default_factory=list)


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "mutation").strip().lower())
    cleaned = cleaned.strip("_") or "mutation"
    if cleaned[0].isdigit():
        cleaned = f"m_{cleaned}"
    return cleaned[:40]


def _make_branch_name(task: str, *, prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    slug = _slugify(task)[:40]
    base = prefix.rstrip("/") + "/"
    return f"{base}{stamp}/{slug}"


def _render_tool_module(tool_name: str, task: str) -> str:
    handler = f"{tool_name}_handler"
    body = 'return tool_result(success=True, timestamp=datetime.now(timezone.utc).isoformat())'
    if "timestamp" not in task.lower():
        body = f'return tool_result(success=True, message="Completed: {task[:120]}")'
    return (
        "from datetime import datetime, timezone\n"
        "from tools.registry import registry, tool_result, tool_error\n\n"
        f"def {handler}(args, **kwargs):\n"
        f"    {body}\n\n"
        "registry.register(\n"
        f'    name="{tool_name}",\n'
        '    toolset="generated",\n'
        "    schema={\n"
        f'        "name": "{tool_name}",\n'
        f'        "description": "{task[:200].replace(chr(34), chr(39))}",\n'
        '        "parameters": {"type": "object", "properties": {}},\n'
        "    },\n"
        f"    handler={handler},\n"
        ")\n"
    )


def default_coding_runner(
    repo_root: Path,
    request: SelfCodingRequest,
    allowed_paths: list[str],
) -> tuple[str, list[str], str | None]:
    _ = allowed_paths
    slug = _slugify(request.task)
    rel_path = f"{request.target_dir.rstrip('/')}/{slug}.py"
    if not is_path_in_mutation_scope(rel_path):
        return "", [], f"path outside mutation scope: {rel_path}"

    content = _render_tool_module(slug, request.task)
    created = create_file(repo_root, rel_path, content)
    if not created.ok:
        return "", [], created.error or "failed to create scoped file"

    diff = show_diff(repo_root, [rel_path])
    if not diff.ok:
        return "", [], diff.error or "failed to collect diff"
    return diff.diff, diff.files or [rel_path], None


async def run_scoped_mutation(
    request: SelfCodingRequest,
    store: MutationStore,
    repo_root: Path,
    *,
    coding_runner: CodingRunner | None = None,
) -> SelfCodingResult:
    settings = get_mutation_settings()
    branch_name = request.branch_name or _make_branch_name(request.task, prefix=settings.branch_prefix)
    allowed_paths = get_allowed_repo_root_relative_paths()
    runner = coding_runner or default_coding_runner

    if not settings.enabled or not settings.self_coding:
        return SelfCodingResult(
            success=False,
            mutation_id=None,
            branch_name=branch_name,
            diff=None,
            test_output=None,
            test_passed=False,
            scope_valid=False,
            error="self-coding mutation is disabled",
        )

    if not is_allowed_target_dir(request.target_dir):
        return SelfCodingResult(
            success=False,
            mutation_id=None,
            branch_name=branch_name,
            diff=None,
            test_output=None,
            test_passed=False,
            scope_valid=False,
            error=f"target_dir not in mutation allowlist: {request.target_dir}",
        )

    repo_root = repo_root.resolve()
    original_branch = current_branch(repo_root)
    created = create_branch(repo_root, branch_name)
    if not created.ok:
        return SelfCodingResult(
            success=False,
            mutation_id=None,
            branch_name=branch_name,
            diff=None,
            test_output=None,
            test_passed=False,
            scope_valid=False,
            error=created.stderr or "failed to create mutation branch",
        )

    try:
        diff_text, files_changed, run_error = runner(repo_root, request, allowed_paths)
        if run_error:
            delete_branch(repo_root, branch_name, checkout=original_branch)
            return SelfCodingResult(
                success=False,
                mutation_id=None,
                branch_name=branch_name,
                diff=None,
                test_output=None,
                test_passed=False,
                scope_valid=False,
                error=run_error,
            )

        scope_ok, violations = validate_diff_scope(diff_text or "")
        if not scope_ok:
            delete_branch(repo_root, branch_name, checkout=original_branch)
            return SelfCodingResult(
                success=False,
                mutation_id=None,
                branch_name=branch_name,
                diff=diff_text,
                test_output=None,
                test_passed=False,
                scope_valid=False,
                error=f"diff scope violation: {', '.join(violations)}",
                files_changed=files_changed,
            )

        test_output: str | None = None
        test_passed = True
        if request.run_tests and settings.require_tests:
            result = run_tests(repo_root)
            test_output = result.output
            test_passed = result.ok

        mutation = store.save_mutation_event(
            workspace_id=request.workspace_id,
            tier="code",
            trigger=request.requested_by,
            status="staged",
            name=_slugify(request.task) or "code_mutation",
            description=request.task,
            source_code=diff_text,
            quality_score=None,
            metadata={
                "branch_name": branch_name,
                "files_changed": files_changed,
                "test_output": test_output,
                "test_passed": test_passed,
                "target_dir": request.target_dir,
                "merged": False,
            },
        )

        success = test_passed
        return SelfCodingResult(
            success=success,
            mutation_id=mutation.id,
            branch_name=branch_name,
            diff=diff_text,
            test_output=test_output,
            test_passed=test_passed,
            scope_valid=True,
            error=None if test_passed else "tests failed; mutation staged for operator review",
            files_changed=files_changed,
        )
    except Exception as exc:
        logger.exception("run_scoped_mutation failed: %s", exc)
        delete_branch(repo_root, branch_name, checkout=original_branch)
        return SelfCodingResult(
            success=False,
            mutation_id=None,
            branch_name=branch_name,
            diff=None,
            test_output=None,
            test_passed=False,
            scope_valid=False,
            error=str(exc),
        )
