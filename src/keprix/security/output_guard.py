"""Guard agent responses before they leave Keprix."""

from __future__ import annotations

import re

from keprix.security.input_sanitizer import InputSanitizer, ThreatLevel


class OutputGuard:
    CREDENTIAL_PATTERNS = [
        r"sk-[a-zA-Z0-9]{32,}",
        r"sk-ant-[a-zA-Z0-9_-]{32,}",
        r"AIza[0-9A-Za-z\-_]{35}",
        r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}",
        r"stripe[_-](?:sk|pk|whsec)_[a-zA-Z0-9]{24,}",
        r"BEGIN\s+(?:RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY",
        r"(?:api[_-]?key|apikey|api_secret|secret_key)[\"\s:=]+([A-Za-z0-9+/]{20,})",
    ]
    PII_PATTERNS = [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
        r"\b\d{3}-\d{2}-\d{4}\b",
    ]
    ZERO_WIDTH_RE = re.compile(r"[​-‏‪-‮﻿]")

    def scan(self, response: str, context: dict | None = None) -> tuple[str, list[str]]:
        del context
        alerts: list[str] = []
        for pattern in self.CREDENTIAL_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                alerts.append("CREDENTIAL_LEAK")
                response = re.sub(pattern, "[CREDENTIAL_REDACTED]", response, flags=re.IGNORECASE)
        for pattern in self.PII_PATTERNS:
            if re.search(pattern, response):
                alerts.append("PII_LEAK_DETECTED")
                response = re.sub(pattern, "[PII_REDACTED]", response)
        injection = InputSanitizer().sanitize(response, source="agent_output")
        if injection.threat_level == ThreatLevel.MALICIOUS:
            alerts.append("OUTPUT_INJECTION_ATTEMPT")
            response = injection.sanitized
        if self.ZERO_WIDTH_RE.search(response):
            alerts.append("STEGANOGRAPHY_DETECTED")
            response = self.ZERO_WIDTH_RE.sub("", response)
        return response, alerts
