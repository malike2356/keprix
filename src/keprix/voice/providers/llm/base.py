"""Voice LLM agent interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from keprix.voice.caller_context import CallerContext
from keprix.voice.session import VoiceSession


@dataclass
class VoiceAgentResponse:
    text: str
    action: str = "reply"
    metadata: dict | None = None


class VoiceAgent(Protocol):
    is_speaking: bool

    async def load_context(self, caller: str) -> CallerContext:
        ...

    async def respond(self, text: str, session: VoiceSession, context: CallerContext) -> VoiceAgentResponse:
        ...

    async def save_to_memory(self, session: VoiceSession, text: str, response: VoiceAgentResponse) -> None:
        ...
