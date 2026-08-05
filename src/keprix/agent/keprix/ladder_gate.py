"""Ponytail gate for mutation output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from keprix.agent.ladder_mode import get_ladder_mode
from keprix.agent.keprix.schemas import SynthesisResult


@dataclass
class LadderResult:
    status: str
    reasons: list[str] = field(default_factory=list)

    @classmethod
    def passed(cls) -> "LadderResult":
        return cls(status="passed")

    @classmethod
    def revised(cls, reason: str) -> "LadderResult":
        return cls(status="revise", reasons=[reason])

    @property
    def passed_gate(self) -> bool:
        return self.status == "passed"


class LadderGate:
    def validate(self, synthesis: SynthesisResult) -> LadderResult:
        mode = get_ladder_mode().mode
        if mode == "off":
            return LadderResult.passed()
        code = synthesis.tool_code
        if re.search(r"^\s*(requests|numpy|pandas|httpx|aiohttp)\s*==", synthesis.skill_yaml, re.M):
            return LadderResult.revised("Ponytail rung 5: avoid adding a new dependency when existing code or stdlib can do it.")
        if code.count("class ") > 1 and "ABC" in code:
            return LadderResult.revised("Ponytail YAGNI: generated code introduces abstraction before a second implementation exists.")
        if len(code.splitlines()) > 220 and "ponytail:" not in code:
            return LadderResult.revised("Ponytail shrink: generated code is large and has no marked simplification boundary.")
        return LadderResult.passed()
