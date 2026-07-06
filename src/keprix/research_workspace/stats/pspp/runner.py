"""PSPP CLI runner."""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.research_workspace.datasets.codebook import Codebook
from keprix.research_workspace.schemas import new_trace_id
from keprix.research_workspace.stats.pspp.errors import PSPPNotInstalledError, PSPPRunError
from keprix.research_workspace.stats.pspp.output_parser import parse_output_file
from keprix.research_workspace.stats.pspp.syntax import generate_analysis_syntax

SETUP_INSTRUCTIONS = (
    "PSPP is not installed. Install PSPP locally, then rerun the analysis.\n"
    "Debian/Ubuntu: sudo apt install pspp\n"
    "macOS (Homebrew): brew install pspp\n"
    "Fedora: sudo dnf install pspp\n"
    "Verify with: pspp --version"
)


@dataclass
class PsppDetection:
    installed: bool
    binary: str | None
    version: str | None
    setup_instructions: str


def detect_pspp() -> PsppDetection:
    binary = shutil.which("pspp")
    if not binary:
        return PsppDetection(False, None, None, SETUP_INSTRUCTIONS)
    try:
        completed = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        version = (completed.stdout or completed.stderr or "").strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        version = None
    return PsppDetection(True, binary, version, SETUP_INSTRUCTIONS)


class PsppRunner:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.root = store.plane.root / "pspp_runs"
        self.root.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        *,
        project_id: str,
        dataset_id: str,
        codebook: Codebook,
        data_path: Path,
        procedures: list[dict[str, Any]] | None = None,
        approve_external_paths: bool = False,
    ) -> dict[str, Any]:
        trace_id = new_trace_id()
        run_id = f"pspp-{uuid.uuid4().hex[:10]}"
        workdir = self.root / run_id
        workdir.mkdir(parents=True, exist_ok=True)
        syntax_text = generate_analysis_syntax(
            codebook=codebook,
            data_path=data_path,
            workspace_root=self.store.plane.root,
            procedures=procedures,
            approve_external_paths=approve_external_paths,
        )
        syntax_path = workdir / "analysis.sps"
        syntax_path.write_text(syntax_text, encoding="utf-8")
        manifest = {
            "run_id": run_id,
            "trace_id": trace_id,
            "dataset_id": dataset_id,
            "dataset_version": codebook.version_id,
            "syntax_path": str(syntax_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "procedures": procedures or [],
        }
        (workdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.store.save_object(
            object_id=run_id,
            object_type="statistical_output",
            project_id=project_id,
            owner="pspp",
            source_ref=str(syntax_path),
            provenance={"dataset_id": dataset_id, "tool": "pspp", "phase": "syntax"},
            payload=manifest,
            trace_id=trace_id,
        )
        return manifest

    def run(
        self,
        *,
        project_id: str,
        run_id: str,
        output_format: str = "txt",
    ) -> dict[str, Any]:
        detection = detect_pspp()
        workdir = self.root / run_id
        syntax_path = workdir / "analysis.sps"
        if not syntax_path.exists():
            raise PSPPRunError(f"PSPP run not found: {run_id}")
        manifest_path = workdir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        if not detection.installed:
            return {
                "run_id": run_id,
                "installed": False,
                "setup_instructions": detection.setup_instructions,
                "syntax_path": str(syntax_path),
                "status": "syntax_only",
                "warnings": ["PSPP binary not found; syntax artifact preserved."],
            }
        ext = {"html": ".html", "odt": ".odt", "txt": ".txt"}.get(output_format, ".txt")
        output_path = workdir / f"output{ext}"
        try:
            completed = subprocess.run(
                [detection.binary, str(syntax_path), "-o", str(output_path)],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PSPPRunError(f"PSPP execution failed: {exc}") from exc
        parsed = parse_output_file(output_path) if output_path.exists() else {"tables": [], "format": output_format}
        result = {
            "run_id": run_id,
            "installed": True,
            "status": "complete" if completed.returncode == 0 else "failed",
            "return_code": completed.returncode,
            "syntax_path": str(syntax_path),
            "output_path": str(output_path) if output_path.exists() else None,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "parsed_tables": parsed.get("tables", []),
            "warnings": [] if completed.returncode == 0 else ["PSPP returned a non-zero exit code."],
            "trace_id": manifest.get("trace_id"),
            "dataset_version": manifest.get("dataset_version"),
        }
        self.store.save_object(
            object_id=f"{run_id}-output",
            object_type="statistical_output",
            project_id=project_id,
            owner="pspp",
            source_ref=str(output_path) if output_path.exists() else str(syntax_path),
            provenance={"run_id": run_id, "tool": "pspp", "phase": "output"},
            payload=result,
            trace_id=str(manifest.get("trace_id") or new_trace_id()),
        )
        return result
