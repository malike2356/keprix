"""Credential and secret redaction for agent output."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field

from keprix.config.settings import get_settings
from keprix.security.patterns import SECRET_PATTERNS, SecretPattern

logger = logging.getLogger(__name__)


@dataclass
class Redactor:
    redact_private_ips: bool = False
    _custom_patterns: list[SecretPattern] = field(default_factory=list)

    def add_pattern(self, name: str, pattern: str) -> None:
        self._custom_patterns.append(
            SecretPattern(
                name=name,
                pattern=re.compile(pattern, re.MULTILINE | re.DOTALL),
                replacement=f"[REDACTED:{name}]",
            )
        )

    def _active_patterns(self) -> list[SecretPattern]:
        patterns = list(SECRET_PATTERNS)
        if not self.redact_private_ips:
            patterns = [item for item in patterns if item.name != "private_ip"]
        return patterns + self._custom_patterns

    def redact(self, text: str) -> str:
        if not text:
            return text
        result = text
        fired: list[str] = []
        for item in self._active_patterns():
            if item.pattern.search(result):
                fired.append(item.name)
                if item.name == "connection_string":
                    result = item.pattern.sub(item.replacement, result)
                else:
                    result = item.pattern.sub(item.replacement, result)
        if fired:
            original_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            self.audit_redaction(original_hash, result, fired)
        return result

    def audit_redaction(self, original_hash: str, redacted: str, patterns_fired: list[str]) -> None:
        logger.info(
            "Redaction applied patterns=%s original_sha256=%s redacted_length=%d",
            ",".join(patterns_fired),
            original_hash,
            len(redacted),
        )


_redactor: Redactor | None = None


def get_redactor() -> Redactor:
    global _redactor
    if _redactor is None:
        settings = get_settings()
        _redactor = Redactor(redact_private_ips=settings.redact_private_ips)
    return _redactor
