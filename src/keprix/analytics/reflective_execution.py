"""Reflective code repair loop."""

from __future__ import annotations

from dataclasses import dataclass, field

from keprix.analytics.code_interpreter import AnalyticsSession, CodeInterpreter


@dataclass(slots=True)
class RevisionTrail:
    attempts: list[dict[str, str]] = field(default_factory=list)


class ReflectiveExecutor:
    def __init__(self, interpreter: CodeInterpreter | None = None) -> None:
        self.interpreter = interpreter or CodeInterpreter()

    def run_with_repair(
        self,
        session: AnalyticsSession,
        code: str,
        *,
        namespace: dict | None = None,
        max_retries: int = 1,
    ) -> tuple[bool, RevisionTrail]:
        trail = RevisionTrail()
        current = code
        for attempt in range(max_retries + 1):
            _verification, result = self.interpreter.run_code(session, current, namespace)
            trail.attempts.append({"code": current, "ok": str(result.ok), "error": result.stderr})
            if result.ok:
                return True, trail
            if attempt < max_retries:
                current = self.repair_code(current, result.stderr)
        return False, trail

    def repair_code(self, code: str, error: str) -> str:
        repaired = code.replace("pritn(", "print(")
        repaired = repaired.replace("leng(", "len(")
        return repaired
