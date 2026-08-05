"""Optional NotebookLM-style external bridge."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keprix_constants import get_config_path
from keprix.research.notebook_job_store import NotebookSource


@dataclass
class NotebookResearchConfig:
    enabled: bool = True
    native_max_sources: int = 20
    external_enabled: bool = False
    external_command: str = ""
    external_mcp_url: str = ""


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off", ""}


def _yaml_config() -> dict[str, Any]:
    path = get_config_path()
    if not Path(path).is_file():
        return {}
    try:
        import yaml

        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    notebook = data.get("notebook_research") if isinstance(data, dict) else {}
    return notebook if isinstance(notebook, dict) else {}


def load_notebook_research_config() -> NotebookResearchConfig:
    cfg = _yaml_config()
    external = cfg.get("external") if isinstance(cfg.get("external"), dict) else {}
    command = os.getenv("NOTEBOOKLM_BRIDGE_CMD", "").strip() or str(external.get("command") or "").strip()
    mcp_url = os.getenv("NOTEBOOKLM_MCP_URL", "").strip() or str(external.get("mcp_url") or "").strip()
    return NotebookResearchConfig(
        enabled=_bool(os.getenv("KEPRIX_NOTEBOOK_RESEARCH_ENABLED", cfg.get("enabled", True)), True),
        native_max_sources=int(cfg.get("native_max_sources") or 20),
        external_enabled=_bool(external.get("enabled"), False) or bool(command or mcp_url),
        external_command=command,
        external_mcp_url=mcp_url,
    )


def notebook_external_available() -> bool:
    config = load_notebook_research_config()
    return config.enabled and config.external_enabled and bool(config.external_command or config.external_mcp_url)


class NotebookExternalBridge:
    def __init__(self, config: NotebookResearchConfig | None = None, timeout: int = 30) -> None:
        self.config = config or load_notebook_research_config()
        self.timeout = timeout

    def run(self, *, query: str, sources: list[NotebookSource]) -> dict[str, Any]:
        if not (self.config.enabled and self.config.external_enabled and (self.config.external_command or self.config.external_mcp_url)):
            raise RuntimeError("Notebook external bridge is not configured")
        payload = {
            "query": query,
            "sources": [source.to_dict() for source in sources],
            "tools": ["notebook_create", "notebook_add_source", "notebook_query", "notebook_export"],
        }
        if self.config.external_command:
            return self._run_command(payload)
        return self._run_mcp(payload)

    def _run_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        command = shlex.split(self.config.external_command)
        completed = subprocess.run(
            command,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "Notebook bridge command failed").strip())
        stdout = completed.stdout.strip()
        if not stdout:
            raise RuntimeError("Notebook bridge command returned no output")
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            data = {"report_md": stdout, "citations": []}
        if not isinstance(data, dict):
            raise RuntimeError("Notebook bridge command returned an invalid payload")
        return data

    def _run_mcp(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.config.external_mcp_url:
            raise RuntimeError("NOTEBOOKLM_MCP_URL is not configured")
        request = urllib.request.Request(
            self.config.external_mcp_url,
            data=json.dumps({"tool": "notebook_query", "arguments": payload}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Notebook MCP returned HTTP {exc.code}") from exc
        except OSError as exc:
            raise RuntimeError(f"Notebook MCP unreachable: {exc}") from exc
        if isinstance(data, dict) and "result" in data:
            data = data["result"]
        if not isinstance(data, dict):
            return {"report_md": str(data), "citations": []}
        return data
