"""Error paste loop entrypoint."""
from __future__ import annotations
from typing import Any
from keprix.agent_os.workflows.error_paste import analyze_error_paste

def run(input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    form = (context or {}).get("form") or {}
    error_text = str(form.get("error_text") or input_text or "")
    extra = str(form.get("context") or "")
    return analyze_error_paste(error_text=error_text, context=extra)
