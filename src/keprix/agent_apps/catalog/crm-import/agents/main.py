"""CRM Import Cleaner entrypoint."""

from __future__ import annotations

from typing import Any

from keprix.agent_os.workflows.crm_import import clean_crm_import


def run(input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    form = (context or {}).get("form") or {}
    csv_text = str(form.get("csv_text") or input_text or "")
    target = str(form.get("target") or "generic")
    result = clean_crm_import(csv_text=csv_text, target=target)
    if result.get("status") == "ok":
        result["artifact"] = {**(result.get("artifact") or {}), "auto_skill": True}
    return result
