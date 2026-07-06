"""Sandbox adapters (Prompt 56)."""

from __future__ import annotations

from typing import Any

from keprix.backend.tools.adapters.base import AdapterResult, ToolAdapter


class SandboxAdapter(ToolAdapter):
    category = "sandboxes"
    risk_level = "high"
    requires_approval_for_write = True
    supports_dry_run = True

    def __init__(self, *, name: str, env_key: str, setup_doc: str) -> None:
        self.name = name
        self.required_env = (env_key,)
        self.setup_doc = setup_doc

    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        command = str(params.get("command") or params.get("code") or "")
        return AdapterResult(
            ok=True,
            data={"sandbox": self.name, "action": action, "command": command, "stdout": "", "stderr": ""},
        )


SANDBOX_ADAPTERS: list[ToolAdapter] = [
    SandboxAdapter(name="e2b", env_key="E2B_API_KEY", setup_doc="Configure E2B for isolated code execution."),
    SandboxAdapter(name="daytona", env_key="DAYTONA_API_KEY", setup_doc="Configure Daytona sandbox API."),
]
