"""Gherkin-style browser QA runner."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from keprix.browser.action_engine import ActionEngine


@dataclass
class QaStepResult:
    step: str
    status: str
    detail: str = ""


@dataclass
class QaReport:
    scenario: str
    passed: bool
    session_id: str
    steps: list[QaStepResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "passed": self.passed,
            "session_id": self.session_id,
            "steps": [asdict(step) for step in self.steps],
        }


class BrowserQaRunner:
    def __init__(self, engine: ActionEngine) -> None:
        self._engine = engine

    def run_scenario(self, scenario: str, *, url: str = "about:blank") -> QaReport:
        session = self._engine.create_session(objective=scenario, url=url)
        steps: list[QaStepResult] = []
        for raw_line in scenario.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lowered = line.lower()
            if lowered.startswith("given"):
                url_match = re.search(r"https?://\S+", line)
                if url_match:
                    target = url_match.group(0).rstrip('"').rstrip("'")
                    self._engine.run_action(session.session_id, action="navigate", value=target)
                    steps.append(QaStepResult(step=line, status="passed", detail=f"navigated to {target}"))
                else:
                    steps.append(QaStepResult(step=line, status="skipped", detail="no URL found"))
            elif lowered.startswith("when") and "search" in lowered:
                self._engine.run_action(session.session_id, action="fill", selector="search", value="test")
                steps.append(QaStepResult(step=line, status="passed"))
            elif lowered.startswith("then") and "screenshot" in lowered:
                result = self._engine.run_action(session.session_id, action="read_page")
                shot = result.get("screenshot_id")
                steps.append(
                    QaStepResult(
                        step=line,
                        status="passed" if shot else "failed",
                        detail=f"screenshot_id={shot}" if shot else "missing screenshot",
                    )
                )
            else:
                steps.append(QaStepResult(step=line, status="skipped", detail="no handler"))
        passed = any(step.status == "passed" for step in steps) and all(
            step.status in ("passed", "skipped") for step in steps
        )
        return QaReport(scenario=scenario, passed=passed, session_id=session.session_id, steps=steps)
