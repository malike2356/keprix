"""Memory System workflow entrypoint."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from keprix.agent_os.workflows.memory_system import run_memory_system


def run(input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    form = (context or {}).get("form") or {}
    query = str(form.get("query") or input_text or "").strip()
    note = str(form.get("note") or "").strip()
    messages = None
    session_id = None
    if note:
        session_id = f"memory-{uuid4().hex[:10]}"
        messages = [
            {"role": "user", "content": note},
            {"role": "assistant", "content": "Captured into the single vault memory system."},
        ]
    result = asyncio.run(
        run_memory_system(query=query, session_id=session_id, messages=messages, title="Memory capture")
    )
    result["artifact"] = {**(result.get("artifact") or {}), "auto_skill": True}
    return result
