"""Extract repeatable task evidence from workspace sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionTaskEvidence:
    session_id: str
    description: str
    tools_used: list[str] = field(default_factory=list)
    estimated_tokens: int = 0


def first_user_task(session_id: str, messages: list[dict[str, Any]]) -> SessionTaskEvidence | None:
    description = ""
    estimated_tokens = 0
    tools: list[str] = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            estimated_tokens += max(1, len(content.split()))
        if not description and message.get("role") == "user" and isinstance(content, str) and content.strip():
            description = content.strip()
        for call in message.get("tool_calls") or []:
            name = call.get("name") or call.get("function", {}).get("name")
            if name:
                tools.append(str(name))
    if not description:
        return None
    return SessionTaskEvidence(
        session_id=session_id,
        description=description,
        tools_used=sorted(set(tools)),
        estimated_tokens=estimated_tokens,
    )
