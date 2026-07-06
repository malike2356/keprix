"""Automation tool adapters (Prompt 56)."""

from __future__ import annotations

from typing import Any

from keprix.backend.tools.adapters.base import AdapterResult, ToolAdapter


class AutomationAdapter(ToolAdapter):
    category = "automation"
    risk_level = "high"
    requires_approval_for_write = True
    supports_dry_run = True

    def __init__(self, *, name: str, env_key: str = "", setup_doc: str = "") -> None:
        self.name = name
        self.required_env = (env_key,) if env_key else ()
        self.setup_doc = setup_doc

    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        payload = {"action": action, "params": params, "adapter": self.name}
        return AdapterResult(ok=True, data={"executed": True, **payload})


AUTOMATION_ADAPTERS: list[ToolAdapter] = [
    AutomationAdapter(name="zapier", env_key="ZAPIER_WEBHOOK_URL", setup_doc="Configure a Zapier catch hook URL."),
    AutomationAdapter(name="keprix_automation_generate", setup_doc="Generates keprix automation drafts."),
    AutomationAdapter(name="keprix_automation_invoke", setup_doc="Invokes approved keprix automations."),
]
