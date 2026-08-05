"""Response quality scorer: heuristic and LLM-judge based scoring."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

JudgeFn = Callable[[str, str, str], Awaitable[float]]  # (prompt, response, rubric) -> 0.0-1.0


@dataclass
class ScoreResult:
    score: float              # 0.0 (bad) to 1.0 (perfect)
    label: str                # "pass" | "warn" | "fail"
    reasons: list[str] = field(default_factory=list)
    provider: str = ""
    model: str = ""

    @classmethod
    def from_score(cls, score: float, provider: str = "", model: str = "") -> "ScoreResult":
        if score >= 0.8:
            label = "pass"
        elif score >= 0.5:
            label = "warn"
        else:
            label = "fail"
        return cls(score=round(score, 3), label=label, provider=provider, model=model)


class ResponseScorer:
    """Score an LLM response against heuristics and optional LLM judge.

    Heuristic checks (always run, no LLM needed):
      - Response is non-empty
      - Response does not contain refusal markers ("I cannot", "I'm sorry, but...")
      - Response length is within a reasonable range
      - No obvious repetition (first / last 50 chars not identical)

    LLM judge (optional, runs only when ``judge_fn`` is provided):
      - Passes prompt + response + rubric to the judge function
      - Judge returns a float 0.0-1.0
    """

    _REFUSAL_MARKERS = (
        "i cannot", "i can't", "i'm sorry, but", "as an ai",
        "i'm not able", "i am unable", "i must decline",
    )

    def __init__(
        self,
        min_length: int = 20,
        max_length: int = 100_000,
        judge_fn: JudgeFn | None = None,
        judge_weight: float = 0.5,
    ) -> None:
        self._min = min_length
        self._max = max_length
        self._judge_fn = judge_fn
        self._judge_weight = judge_weight

    async def score(
        self,
        prompt: str,
        response: str,
        rubric: str = "",
        provider: str = "",
        model: str = "",
    ) -> ScoreResult:
        """Return a composite score for the response."""
        heuristic_score, reasons = self._heuristic(response)

        if self._judge_fn and rubric:
            try:
                judge_score = await self._judge_fn(prompt, response, rubric)
                judge_score = max(0.0, min(1.0, judge_score))
                w = self._judge_weight
                composite = heuristic_score * (1 - w) + judge_score * w
                reasons.append(f"judge={judge_score:.2f}")
            except Exception as exc:
                logger.warning("Judge fn failed: %s", exc)
                composite = heuristic_score
        else:
            composite = heuristic_score

        result = ScoreResult.from_score(composite, provider=provider, model=model)
        result.reasons = reasons
        return result

    def _heuristic(self, response: str) -> tuple[float, list[str]]:
        reasons: list[str] = []
        score = 1.0

        if not response or not response.strip():
            return 0.0, ["empty_response"]

        length = len(response)
        if length < self._min:
            score -= 0.4
            reasons.append(f"too_short({length})")
        elif length > self._max:
            score -= 0.1
            reasons.append("too_long")

        lower = response.lower()
        for marker in self._REFUSAL_MARKERS:
            if marker in lower:
                score -= 0.3
                reasons.append(f"refusal:{marker[:20]}")
                break

        if len(response) > 100 and response[:50] == response[-50:]:
            score -= 0.3
            reasons.append("repetition_detected")

        if not reasons:
            reasons.append("ok")

        return max(0.0, min(1.0, score)), reasons
