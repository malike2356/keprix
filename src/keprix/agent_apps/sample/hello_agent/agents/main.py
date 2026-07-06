"""Sample hello agent entrypoint."""

from __future__ import annotations

from typing import Any


def run(input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    form = (context or {}).get("form") or {}
    name = str(form.get("name") or input_text or "world").strip() or "world"
    return {
        "status": "ok",
        "output": f"Hello from hello-agent: {name}",
        "artifact": {"type": "greeting", "name": name},
    }
