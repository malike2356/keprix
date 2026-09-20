"""Default and alternate Providers for each seam."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from keprix.seams.ids import SEAM_RELATED_TOOLS
from keprix.seams.policy import related_tool_schema_stubs, resolve_under_root


class LocalFsProvider:
    """Host filesystem Provider (cwd-relative by default)."""

    provider_id = "fs.local"

    def __init__(self, root: str | Path | None = None) -> None:
        self._root = Path(root).resolve() if root else Path.cwd().resolve()

    def read_text(self, path: str, *, encoding: str = "utf-8") -> str:
        target = resolve_under_root(self._root, path)
        return target.read_text(encoding=encoding)

    def write_text(self, path: str, content: str, *, encoding: str = "utf-8") -> None:
        target = resolve_under_root(self._root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)

    def exists(self, path: str) -> bool:
        try:
            return resolve_under_root(self._root, path).exists()
        except Exception:
            return False

    def list_dir(self, path: str = ".") -> list[str]:
        target = resolve_under_root(self._root, path)
        if not target.is_dir():
            return []
        return sorted(p.name for p in target.iterdir())

    def tool_schemas(self) -> list[dict[str, Any]]:
        return related_tool_schema_stubs("fs")


class SandboxedFsProvider:
    """Tempdir-only filesystem Provider for swap demos and tests."""

    provider_id = "fs.sandboxed"

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def read_text(self, path: str, *, encoding: str = "utf-8") -> str:
        return resolve_under_root(self._root, path).read_text(encoding=encoding)

    def write_text(self, path: str, content: str, *, encoding: str = "utf-8") -> None:
        target = resolve_under_root(self._root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)

    def exists(self, path: str) -> bool:
        try:
            return resolve_under_root(self._root, path).exists()
        except Exception:
            return False

    def list_dir(self, path: str = ".") -> list[str]:
        target = resolve_under_root(self._root, path)
        if not target.is_dir():
            return []
        return sorted(p.name for p in target.iterdir())

    def tool_schemas(self) -> list[dict[str, Any]]:
        # Same related tools as local; swap must not force consumer rewrites.
        return related_tool_schema_stubs("fs")


class LocalShellProvider:
    """Local subprocess Provider (thin; production terminal uses environments/)."""

    provider_id = "shell.local"

    def __init__(self, cwd: str | Path | None = None) -> None:
        self._cwd = str(Path(cwd).resolve() if cwd else Path.cwd())

    def execute(
        self,
        command: str,
        *,
        cwd: str = "",
        timeout: int | None = None,
    ) -> dict[str, Any]:
        effective_cwd = cwd or self._cwd
        try:
            completed = subprocess.run(
                ["bash", "-lc", command],
                capture_output=True,
                text=True,
                cwd=effective_cwd,
                timeout=timeout or 60,
                check=False,
            )
            output = (completed.stdout or "") + (completed.stderr or "")
            return {"output": output, "returncode": int(completed.returncode)}
        except subprocess.TimeoutExpired as exc:
            return {
                "output": f"timeout: {exc}",
                "returncode": 124,
                "error_code": "shell_timeout",
            }

    def tool_schemas(self) -> list[dict[str, Any]]:
        return related_tool_schema_stubs("shell")


class SandboxedShellProvider:
    """Shell Provider confined to a sandbox cwd (no host escape via cwd)."""

    provider_id = "shell.sandboxed"

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        command: str,
        *,
        cwd: str = "",
        timeout: int | None = None,
    ) -> dict[str, Any]:
        # Force cwd under sandbox root; ignore caller cwd escapes.
        effective = self._root
        if cwd:
            try:
                effective = resolve_under_root(self._root, cwd)
            except Exception:
                effective = self._root
        (self._root / "tmp").mkdir(parents=True, exist_ok=True)
        try:
            completed = subprocess.run(
                ["bash", "-lc", command],
                capture_output=True,
                text=True,
                cwd=str(effective),
                timeout=timeout or 60,
                check=False,
                env={
                    **os.environ,
                    "HOME": str(self._root),
                    "TMPDIR": str(self._root / "tmp"),
                },
            )
            output = (completed.stdout or "") + (completed.stderr or "")
            return {
                "output": output,
                "returncode": int(completed.returncode),
                "sandbox_root": str(self._root),
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "output": f"timeout: {exc}",
                "returncode": 124,
                "error_code": "shell_timeout",
                "sandbox_root": str(self._root),
            }

    def tool_schemas(self) -> list[dict[str, Any]]:
        return related_tool_schema_stubs("shell")


class DefaultMemoryProvider:
    """Workspace-scoped memory Provider backed by MEMORY.md / USER.md layout."""

    provider_id = "memory.default"

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir else None

    def _dir(self, workspace_id: str | None) -> Path:
        if self._base is not None:
            root = self._base
        else:
            try:
                from tools.memory_tool import get_memory_dir

                root = get_memory_dir()
            except Exception:
                from keprix_constants import get_keprix_home

                root = get_keprix_home() / "memories"
        if workspace_id:
            root = root / f"ws_{workspace_id}"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def read_store(self, store: str, *, workspace_id: str | None = None) -> str:
        name = store if store.endswith(".md") else f"{store}.md"
        path = self._dir(workspace_id) / name
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def append_entry(
        self,
        store: str,
        entry: str,
        *,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        name = store if store.endswith(".md") else f"{store}.md"
        path = self._dir(workspace_id) / name
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        delimiter = "\n§\n"
        if existing.strip():
            path.write_text(existing.rstrip() + delimiter + entry.strip() + "\n", encoding="utf-8")
        else:
            path.write_text(entry.strip() + "\n", encoding="utf-8")
        return {"success": True, "store": name, "workspace_id": workspace_id}

    def tool_schemas(self) -> list[dict[str, Any]]:
        return related_tool_schema_stubs("memory")


class DefaultLlmProvider:
    """LLM route Provider: reports configured route; complete is opt-in stub."""

    provider_id = "llm.default"

    def resolve_route(self) -> dict[str, Any]:
        model = os.environ.get("KEPRIX_MODEL") or os.environ.get("OPENAI_MODEL") or ""
        provider = os.environ.get("KEPRIX_PROVIDER") or ""
        try:
            from keprix_cli.config import load_config

            cfg = load_config() or {}
            model = model or str((cfg.get("model") or {}).get("default") or "")
            provider = provider or str((cfg.get("model") or {}).get("provider") or "")
        except Exception:
            pass
        return {
            "provider": provider or "unset",
            "model": model or "unset",
            "seam": "llm",
        }

    def complete(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        # Default Provider does not burn API keys; callers needing live
        # completion use the agent loop. This returns a structured refusal
        # so consumers can branch without ImportError.
        del kwargs
        return {
            "ok": False,
            "error_code": "llm_provider_stub",
            "message": (
                "llm.default complete() is a seam stub; use the agent loop "
                "or register a live llm Provider."
            ),
            "message_count": len(messages),
            "route": self.resolve_route(),
        }

    def tool_schemas(self) -> list[dict[str, Any]]:
        return related_tool_schema_stubs("llm")


class DefaultSubagentProvider:
    """Subagent Provider describing delegate_task; spawn stays agent-owned."""

    provider_id = "subagent.default"

    def describe(self) -> dict[str, Any]:
        return {
            "seam": "subagent",
            "related_tools": list(SEAM_RELATED_TOOLS["subagent"]),
            "implementation": "tools.delegate_tool.delegate_task",
        }

    def spawn(self, task: str, **kwargs: Any) -> dict[str, Any]:
        # Live spawn requires parent agent context; expose honest stub.
        del kwargs
        return {
            "ok": False,
            "error_code": "subagent_requires_agent_context",
            "message": (
                "subagent.default spawn() requires AIAgent parent context; "
                "use delegate_task from the agent loop."
            ),
            "task_preview": (task or "")[:200],
            "describe": self.describe(),
        }

    def tool_schemas(self) -> list[dict[str, Any]]:
        return related_tool_schema_stubs("subagent")


class DefaultWebProvider:
    """Web Provider metadata + offline-safe stubs for search/fetch."""

    provider_id = "web.default"

    def search(self, query: str, *, limit: int = 5) -> dict[str, Any]:
        return {
            "ok": False,
            "error_code": "web_provider_offline_stub",
            "message": (
                "web.default search() is a seam stub; live search remains on "
                "tools.web_tools / configured BYOK providers."
            ),
            "query": query,
            "limit": limit,
            "related_tools": list(SEAM_RELATED_TOOLS["web"]),
        }

    def fetch(self, url: str, **kwargs: Any) -> dict[str, Any]:
        del kwargs
        return {
            "ok": False,
            "error_code": "web_provider_offline_stub",
            "message": (
                "web.default fetch() is a seam stub; live fetch remains on "
                "web_extract / browser tools."
            ),
            "url": url,
        }

    def tool_schemas(self) -> list[dict[str, Any]]:
        return related_tool_schema_stubs("web")
