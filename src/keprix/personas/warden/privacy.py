"""Data privacy and PII scanning for WARDEN."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from keprix.personas.warden.auditor import Severity
from keprix.personas.warden.persona import WARDEN_PERSONA
from keprix.security.patterns import SECRET_PATTERNS
from keprix.security.redactor import get_redactor
from keprix.security.secret_scan import get_secret_scanner


PII_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        Severity.MEDIUM,
    ),
    (
        "phone",
        re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"),
        Severity.MEDIUM,
    ),
    (
        "uk_ni_number",
        re.compile(r"\b[A-Z]{2}\d{6}[A-D]\b"),
        Severity.HIGH,
    ),
    (
        "credit_card",
        re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        Severity.CRITICAL,
    ),
]


@dataclass(slots=True)
class PrivacyFinding:
    pattern: str
    severity: str
    message: str
    redacted_preview: str
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "severity": self.severity,
            "message": self.message,
            "redacted_preview": self.redacted_preview,
            "count": self.count,
        }


@dataclass
class PrivacyScanResult:
    passed: bool
    findings: list[PrivacyFinding] = field(default_factory=list)
    sanitized_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "findings": [finding.to_dict() for finding in self.findings],
            "sanitized_text": self.sanitized_text,
        }


class WardenPrivacy:
    def __init__(self) -> None:
        self.persona = WARDEN_PERSONA
        self._redactor = get_redactor()
        self._secret_scanner = get_secret_scanner()

    def scan(self, text: str) -> PrivacyScanResult:
        if not text:
            return PrivacyScanResult(passed=True, sanitized_text="")

        findings: list[PrivacyFinding] = []

        for name, pattern, severity in PII_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                sample = matches[0] if isinstance(matches[0], str) else str(matches[0])
                findings.append(
                    PrivacyFinding(
                        pattern=name,
                        severity=severity,
                        message=f"PII pattern detected: {name}",
                        redacted_preview=self._redactor.redact(sample)[:80],
                        count=len(matches),
                    )
                )

        for secret in SECRET_PATTERNS:
            if secret.pattern.search(text):
                findings.append(
                    PrivacyFinding(
                        pattern=f"secret_{secret.name}",
                        severity=Severity.CRITICAL,
                        message=f"Secret pattern detected: {secret.name}",
                        redacted_preview=f"[REDACTED:{secret.name}]",
                    )
                )

        blocking = {finding.severity for finding in findings} & {
            Severity.CRITICAL,
            Severity.HIGH,
        }
        sanitized = self._secret_scanner.scan_and_sanitize(text)
        sanitized = self._redactor.redact(sanitized)

        return PrivacyScanResult(
            passed=not blocking,
            findings=findings,
            sanitized_text=sanitized,
        )

    def scan_files(self, files: dict[str, str]) -> PrivacyScanResult:
        combined_findings: list[PrivacyFinding] = []
        sanitized_parts: list[str] = []
        passed = True

        for path, content in files.items():
            result = self.scan(content)
            passed = passed and result.passed
            for finding in result.findings:
                finding.message = f"{finding.message} in {path}"
                combined_findings.append(finding)
            sanitized_parts.append(f"--- {path} ---\n{result.sanitized_text}")

        return PrivacyScanResult(
            passed=passed,
            findings=combined_findings,
            sanitized_text="\n\n".join(sanitized_parts),
        )

    def recommend_actions(self, result: PrivacyScanResult) -> list[str]:
        actions: list[str] = []
        patterns = {finding.pattern for finding in result.findings}

        if any(p.startswith("secret_") for p in patterns):
            actions.append("Rotate exposed credentials and store replacements in the vault")
        if "email" in patterns or "phone" in patterns:
            actions.append("Redact PII before logging or exporting data")
        if "credit_card" in patterns:
            actions.append("Remove card data immediately; review PCI compliance scope")
        if not actions:
            actions.append("No privacy remediation required")
        return actions
