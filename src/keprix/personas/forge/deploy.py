"""Build and deployment pipeline for FORGE."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keprix.agent_apps.deployment_bundle import build_deployment_bundle
from keprix.coding.lint_test_runner import (
    CommandResult,
    detect_lint_command,
    detect_test_command,
    run_lint,
    run_tests,
)
from keprix.personas.forge.persona import FORGE_PERSONA


@dataclass(slots=True)
class DeployResult:
    ok: bool
    stage: str
    command: str = ""
    output: str = ""
    artifacts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "stage": self.stage,
            "command": self.command,
            "output": self.output,
            "artifacts": list(self.artifacts),
            "errors": list(self.errors),
        }


class ForgeDeployPipeline:
    def __init__(self, *, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.persona = FORGE_PERSONA

    def detect_build_targets(self) -> dict[str, Any]:
        root = self.project_root
        targets: dict[str, Any] = {
            "docker": (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists(),
            "python": (root / "pyproject.toml").exists() or (root / "requirements.txt").exists(),
            "node": (root / "package.json").exists(),
            "make": (root / "Makefile").exists(),
        }
        targets["test_command"] = detect_test_command(root)
        targets["lint_command"] = detect_lint_command(root)
        if targets["docker"]:
            targets["build_command"] = "docker build -t forge-build ."
        elif targets["node"]:
            targets["build_command"] = "npm run build --if-present"
        elif targets["make"] and (root / "Makefile").exists():
            makefile = (root / "Makefile").read_text(encoding="utf-8", errors="ignore")
            targets["build_command"] = "make build" if re.search(r"^build:", makefile, re.M) else None
        else:
            targets["build_command"] = None
        return targets

    def run_build(self) -> DeployResult:
        targets = self.detect_build_targets()
        lint_result = run_lint(self.project_root, targets.get("lint_command"))
        if not lint_result.ok:
            return DeployResult(
                ok=False,
                stage="lint",
                command=lint_result.command,
                output=lint_result.output,
                errors=lint_result.parsed_failures or ["lint failed"],
            )

        build_command = targets.get("build_command")
        if build_command:
            from keprix.coding.lint_test_runner import run_command

            build_result = run_command(build_command, self.project_root)
            return DeployResult(
                ok=build_result.ok,
                stage="build",
                command=build_result.command,
                output=build_result.output,
                errors=build_result.parsed_failures if not build_result.ok else [],
            )

        test_result = self.run_tests()
        return DeployResult(
            ok=test_result.ok,
            stage="test",
            command=test_result.command,
            output=test_result.output,
            errors=test_result.errors,
        )

    def run_tests(self) -> DeployResult:
        targets = self.detect_build_targets()
        test_command = targets.get("test_command")
        if not test_command:
            return DeployResult(ok=True, stage="test", output="no test command detected")
        result: CommandResult = run_tests(self.project_root, test_command)
        return DeployResult(
            ok=result.ok,
            stage="test",
            command=result.command,
            output=result.output,
            errors=result.parsed_failures if not result.ok else [],
        )

    def run_deploy(self, *, target: str = "local", app_name: str | None = None) -> DeployResult:
        build_result = self.run_build()
        if not build_result.ok:
            return build_result

        if app_name:
            app_dir = self.project_root
            bundle_path = self.project_root / "dist" / f"{app_name}.zip"
            bundle_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                bundle_info = build_deployment_bundle(app_dir, bundle_path, target=target)
            except Exception as exc:
                return DeployResult(ok=False, stage="bundle", errors=[str(exc)])
            return DeployResult(
                ok=True,
                stage="deploy",
                output=f"Bundle created: {bundle_info.get('bundle_path', bundle_path)}",
                artifacts=[str(bundle_path)],
            )

        deploy_script = self._generate_deploy_script(target)
        return DeployResult(
            ok=True,
            stage="deploy",
            command=deploy_script,
            output="Deploy script generated; run with approval",
            artifacts=[deploy_script],
        )

    def _generate_deploy_script(self, target: str) -> str:
        targets = self.detect_build_targets()
        lines = ["#!/usr/bin/env bash", "set -euo pipefail", f"# FORGE deploy target: {target}"]
        if targets.get("lint_command"):
            lines.append(targets["lint_command"])
        if targets.get("test_command"):
            lines.append(targets["test_command"])
        if targets.get("build_command"):
            lines.append(targets["build_command"])
        if targets["docker"]:
            lines.append("docker compose up -d --build")
        lines.append('echo "Deploy complete"')
        return "\n".join(lines)
