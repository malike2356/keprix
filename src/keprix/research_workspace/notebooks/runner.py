"""Notebook orchestration service."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from keprix.research_workspace.notebooks.artifacts import collect_artifacts, persist_run_artifacts
from keprix.research_workspace.notebooks.html_export import write_html_report, write_ipynb
from keprix.research_workspace.notebooks.notebook import (
    attach_cell_output,
    build_provenance,
    create_notebook,
    export_script,
)
from keprix.research_workspace.notebooks.python_runner import run_python_script
from keprix.research_workspace.notebooks.r_runner import run_r_script
from keprix.research_workspace.notebooks.sandbox import SandboxConfig, assert_code_allowed, validate_paths
from keprix.research_workspace.schemas import new_trace_id


class NotebookRunner:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.root = store.plane.root / "notebook_runs"
        self.root.mkdir(parents=True, exist_ok=True)

    def prepare_run(
        self,
        *,
        project_id: str,
        runtime: Literal["python", "r"],
        code: str,
        dataset_id: str | None = None,
        dataset_version: int | None = None,
        dataset_path: Path | None = None,
        markdown_cells: list[str] | None = None,
        config: SandboxConfig | None = None,
    ) -> dict[str, Any]:
        config = config or SandboxConfig()
        trace_id = new_trace_id()
        assert_code_allowed(code, config)
        run_id = f"nb-{uuid.uuid4().hex[:10]}"
        workdir = self.root / run_id
        workdir.mkdir(parents=True, exist_ok=True)
        provenance = build_provenance(
            project_id=project_id,
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            trace_id=trace_id,
        )
        notebook = create_notebook(
            code_cells=[code],
            markdown_cells=markdown_cells,
            runtime=runtime,
            provenance=provenance,
        )
        ext = ".py" if runtime == "python" else ".R"
        script_path = workdir / f"analysis{ext}"
        script_path.write_text(code, encoding="utf-8")
        if dataset_path is not None:
            allowlist = list(config.file_allowlist)
            allowlist.append(str(dataset_path))
            config.file_allowlist = allowlist
            validate_paths([dataset_path], workdir=workdir, allowlist=config.file_allowlist)
            linked = workdir / "dataset.csv"
            if not linked.exists():
                linked.write_bytes(dataset_path.read_bytes())
        ipynb_path = write_ipynb(notebook, workdir / "notebook.ipynb")
        manifest = {
            "run_id": run_id,
            "project_id": project_id,
            "runtime": runtime,
            "trace_id": trace_id,
            "dataset_id": dataset_id,
            "dataset_version": dataset_version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "paths": {
                "workdir": str(workdir),
                "script": str(script_path),
                "notebook": ipynb_path,
            },
            "config": {
                "timeout_seconds": config.timeout_seconds,
                "allow_network": config.allow_network,
                "approve_dangerous": config.approve_dangerous,
            },
        }
        (workdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.store.save_object(
            object_id=run_id,
            object_type="notebook_run",
            project_id=project_id,
            owner="notebook",
            source_ref=str(script_path),
            provenance={
                "dataset_id": dataset_id,
                "dataset_version": dataset_version,
                "tool": "notebook",
                "phase": "prepare",
            },
            payload=manifest,
            trace_id=trace_id,
        )
        return manifest

    def execute(
        self,
        *,
        project_id: str,
        run_id: str,
        config: SandboxConfig | None = None,
    ) -> dict[str, Any]:
        config = config or SandboxConfig()
        workdir = self.root / run_id
        manifest_path = workdir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Notebook run not found: {run_id}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        runtime = manifest["runtime"]
        script_path = Path(manifest["paths"]["script"])
        dataset_path = workdir / "dataset.csv"
        ds = dataset_path if dataset_path.exists() else None
        if runtime == "python":
            result = run_python_script(workdir=workdir, script_path=script_path, config=config, dataset_path=ds)
        else:
            result = run_r_script(workdir=workdir, script_path=script_path, config=config, dataset_path=ds)
        notebook = json.loads(Path(manifest["paths"]["notebook"]).read_text(encoding="utf-8"))
        notebook = attach_cell_output(
            notebook,
            cell_index=len(notebook.get("cells") or []) - 1,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.return_code,
            repair_suggestions=result.repair_suggestions,
        )
        write_ipynb(notebook, Path(manifest["paths"]["notebook"]))
        html_path = write_html_report(notebook, workdir / "report.html")
        py_export = workdir / "analysis_export.py"
        if runtime == "python":
            py_export.write_text(export_script(notebook, runtime="python"), encoding="utf-8")
        manifest.update(
            {
                "status": "completed" if result.return_code == 0 else "failed",
                "return_code": result.return_code,
                "repair_suggestions": result.repair_suggestions,
                "artifacts": collect_artifacts(workdir),
                "html_report": html_path,
                "execution_log": result.log_path,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        persisted = persist_run_artifacts(
            workdir=workdir,
            artifact_root=self.root / "artifacts",
            run_id=run_id,
            manifest=manifest,
        )
        manifest["persisted_artifacts"] = persisted
        self.store.save_object(
            object_id=f"{run_id}-output",
            object_type="notebook_run",
            project_id=project_id,
            owner="notebook",
            source_ref=html_path,
            provenance={
                "run_id": run_id,
                "dataset_id": manifest.get("dataset_id"),
                "dataset_version": manifest.get("dataset_version"),
                "tool": "notebook",
                "phase": "output",
            },
            payload=manifest,
            trace_id=str(manifest.get("trace_id") or new_trace_id()),
        )
        return manifest
