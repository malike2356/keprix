"""Video Agent entrypoint."""
from __future__ import annotations
from typing import Any
from keprix.agent_os.workflows.video_agent import generate_video_package

def run(input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    form = (context or {}).get("form") or {}
    topic = str(form.get("topic") or input_text or "").strip()
    audience = str(form.get("audience") or "general")
    try:
        length = int(str(form.get("length_minutes") or "8"))
    except ValueError:
        length = 8
    return generate_video_package(topic=topic, audience=audience, length_minutes=length)
