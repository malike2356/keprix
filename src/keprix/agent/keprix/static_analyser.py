"""AST-based security scan for generated tool code."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from keprix.agent.keprix.ast_analyser import analyse
from keprix.agent.keprix.namespace import validate_tool_imports
from keprix.agent.keprix.schemas import AnalysisResult

_IP_LITERAL = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


class StaticAnalyser:
    def scan(self, code: str) -> AnalysisResult:
        violations = list(analyse(code))
        violations.extend(validate_tool_imports(code))
        violations.extend(self._scan_ip_literals(code))
        return AnalysisResult(safe=not violations, violations=violations, severity="block")

    def _scan_ip_literals(self, code: str) -> list[str]:
        violations: list[str] = []
        for match in _IP_LITERAL.finditer(code):
            violations.append(f"Hardcoded IP literal blocked: {match.group(0)}")
        return violations


static_analyser = StaticAnalyser()
