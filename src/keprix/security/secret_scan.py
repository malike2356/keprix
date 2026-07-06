"""Secret scanning for data at rest."""

from __future__ import annotations

import logging
from typing import Callable

from keprix.security.patterns import SECRET_PATTERNS
from keprix.security.redactor import get_redactor

logger = logging.getLogger(__name__)


class SecretScanner:
    def __init__(self, audit_callback: Callable[[str, list[str]], None] | None = None) -> None:
        self._audit_callback = audit_callback
        self._redactor = get_redactor()

    def scan_and_sanitize(self, text: str) -> str:
        if not text:
            return text
        fired = [item.name for item in SECRET_PATTERNS if item.pattern.search(text)]
        if not fired:
            return text
        if self._audit_callback:
            self._audit_callback(text, fired)
        else:
            logger.warning("Credential pattern detected in stored data patterns=%s", ",".join(fired))
        return self._redactor.redact(text)


_default_scanner: SecretScanner | None = None


def get_secret_scanner() -> SecretScanner:
    global _default_scanner
    if _default_scanner is None:
        _default_scanner = SecretScanner()
    return _default_scanner
