"""Code generation, review, and patch logic for FORGE."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keprix.code_agent.code_agent import CodeAgent, CodeAgentConfig, CodeAgentResult
from keprix.coding.configs import load_profile
from keprix.coding.patcher import PatchBundle, apply_patch_bundle, format_patch
from keprix.coding.review import ReviewDecision, review_file_edit, review_run
from keprix.coding.trajectory import TrajectoryLogger
from keprix.personas.forge.persona import FORGE_PERSONA
from keprix.security.patterns import SECRET_PATTERNS
from keprix.security.redactor import get_redactor

FORGE_SANDBOX_MODE = "non-main"

_HOST_PATH_PREFIXES = ("/etc/", "/usr/", "/var/", "/sys/", "/proc/")


@dataclass(slots=True)
class ForgeSandboxConfig:
    mode: str = FORGE_SANDBOX_MODE
    workspace_id: str = "default"
    provider: str = "docker"
    approval_threshold: str = "medium"

    def to_code_agent_config(self) -> CodeAgentConfig:
        return CodeAgentConfig(
            workspace_id=self.workspace_id,
            provider=self.provider,
            approval_threshold=self.approval_threshold,
        )


@dataclass(slots=True)
class CodeReviewFinding:
    rule: str
    severity: str
    message: str
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
        }


@dataclass
class CodeReviewResult:
    passed: bool
    findings: list[CodeReviewFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "findings": [finding.to_dict() for finding in self.findings],
        }


class ForgeCoder:
    def __init__(
        self,
        *,
        repo_root: Path,
        sandbox: ForgeSandboxConfig | None = None,
        profile_name: str = "human_review",
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.sandbox = sandbox or ForgeSandboxConfig()
        self.profile = load_profile(profile_name)
        self.persona = FORGE_PERSONA
        self._trajectory = TrajectoryLogger()

    def enforce_sandbox(self, target_path: str | Path) -> ReviewDecision:
        path = Path(target_path)
        if self.sandbox.mode != FORGE_SANDBOX_MODE:
            return ReviewDecision(True, False, "sandbox mode allows path")

        resolved = path.resolve() if path.is_absolute() else (self.repo_root / path).resolve()
        path_str = str(resolved)

        for prefix in _HOST_PATH_PREFIXES:
            if path_str.startswith(prefix):
                return ReviewDecision(False, True, f"host-level write blocked in {FORGE_SANDBOX_MODE} mode")

        try:
            resolved.relative_to(self.repo_root)
        except ValueError:
            return ReviewDecision(False, True, f"path outside repo blocked in {FORGE_SANDBOX_MODE} mode")

        return review_file_edit(str(path), self.repo_root)

    def review_code(self, source: str, *, file_path: str = "snippet.py") -> CodeReviewResult:
        findings: list[CodeReviewFinding] = []

        for pattern in SECRET_PATTERNS:
            if pattern.pattern.search(source):
                findings.append(
                    CodeReviewFinding(
                        rule="no_secrets",
                        severity="critical",
                        message=f"Possible secret detected: {pattern.name}",
                    )
                )

        redacted = get_redactor().redact(source)
        if redacted != source:
            findings.append(
                CodeReviewFinding(
                    rule="no_secrets",
                    severity="critical",
                    message="Source contains redactable secret patterns",
                )
            )

        if file_path.endswith(".py"):
            if "def " in source or "class " in source:
                if not re.search(r"def\s+\w+\([^)]*\)\s*->", source) and "def " in source:
                    findings.append(
                        CodeReviewFinding(
                            rule="type_hints",
                            severity="error",
                            message="Python functions should include return type hints",
                        )
                    )
            if "def test_" not in source and ("def " in source or "class " in source):
                findings.append(
                    CodeReviewFinding(
                        rule="tests_required",
                        severity="warning",
                        message="New functionality should include tests",
                    )
                )

        if file_path.endswith((".ts", ".tsx")):
            if re.search(r":\s*any\b", source):
                findings.append(
                    CodeReviewFinding(
                        rule="strict_typescript",
                        severity="error",
                        message="Avoid explicit `any` in TypeScript",
                    )
                )

        blocking = {finding.severity for finding in findings} & {"critical", "error"}
        return CodeReviewResult(passed=not blocking, findings=findings)

    def generate_code(self, task: str, *, code: str | None = None) -> CodeAgentResult:
        agent = CodeAgent(self.sandbox.to_code_agent_config())
        try:
            result = agent.run_task(task, code=code)
        finally:
            agent.close()

        self._trajectory.log(
            "forge_generate",
            {
                "task": task,
                "ok": result.ok,
                "needs_approval": result.needs_approval,
                "sandbox_mode": self.sandbox.mode,
            },
        )
        return result

    def prepare_patch(self, bundle: PatchBundle) -> dict[str, Any]:
        review_findings: list[CodeReviewFinding] = []
        blocked_paths: list[str] = []

        for edit in bundle.edits:
            sandbox_decision = self.enforce_sandbox(edit.path)
            if not sandbox_decision.allowed:
                blocked_paths.append(edit.path)
            if edit.ok and edit.rollback_data.get("new_content"):
                content = str(edit.rollback_data["new_content"])
                review = self.review_code(content, file_path=edit.path)
                review_findings.extend(review.findings)

        run_decision = review_run(self.profile, edits_count=len(bundle.edits))
        needs_approval = run_decision.needs_approval or bool(blocked_paths)
        passed = not blocked_paths and all(f.severity not in {"critical", "error"} for f in review_findings)

        return {
            "patch_text": format_patch(bundle.edits),
            "passed_review": passed and run_decision.allowed,
            "needs_approval": needs_approval or not passed,
            "blocked_paths": blocked_paths,
            "findings": [finding.to_dict() for finding in review_findings],
            "sandbox_mode": self.sandbox.mode,
        }

    def apply_patch_with_approval(self, bundle: PatchBundle, *, approved: bool = False) -> dict[str, Any]:
        prep = self.prepare_patch(bundle)
        if not approved:
            return {**prep, "applied": False, "reason": "approval required"}
        if not prep["passed_review"]:
            return {**prep, "applied": False, "reason": "review failed"}
        if prep["blocked_paths"]:
            return {**prep, "applied": False, "reason": "sandbox blocked host-level writes"}

        applied = apply_patch_bundle(self.repo_root, bundle)
        self._trajectory.log("forge_patch_applied", {"edits": len(applied), "approved": approved})
        return {**prep, "applied": True, "edits_applied": len(applied)}
