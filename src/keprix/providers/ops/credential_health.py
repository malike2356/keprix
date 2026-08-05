"""Credential health checker: verify API keys are present and well-formed."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class CredentialStatus(str, Enum):
    OK      = "ok"
    MISSING = "missing"
    INVALID = "invalid"
    UNKNOWN = "unknown"


@dataclass
class CredentialResult:
    provider: str
    status: CredentialStatus
    env_var: str
    detail: str = ""


# Pattern: (env_var_name, validation_regex_or_None)
_CREDENTIALS: dict[str, tuple[str, str | None]] = {
    "anthropic":   ("ANTHROPIC_API_KEY",  r"^sk-ant-[A-Za-z0-9_\-]{40,}"),
    "openai":      ("OPENAI_API_KEY",     r"^sk-[A-Za-z0-9_\-]{40,}"),
    "gemini":      ("GEMINI_API_KEY",     r"^AIza[A-Za-z0-9_\-]{30,}"),
    "mistral":     ("MISTRAL_API_KEY",    None),
    "groq":        ("GROQ_API_KEY",       r"^gsk_[A-Za-z0-9_]{40,}"),
    "xai":         ("XAI_API_KEY",        r"^xai-[A-Za-z0-9_]{30,}"),
    "deepseek":    ("DEEPSEEK_API_KEY",   None),
    "openrouter":  ("OPENROUTER_API_KEY", None),
    "together":    ("TOGETHER_API_KEY",   None),
    "fireworks":   ("FIREWORKS_API_KEY",  None),
    "cohere":      ("COHERE_API_KEY",     None),
    "pollinations":("POLLINATIONS_KEY",   None),  # optional free key
}


class CredentialHealth:
    """Check that required API credentials are available and well-formed.

    Reads from environment variables. For providers without a known key
    format, the check only verifies the variable is non-empty.

    Usage::

        health = CredentialHealth()
        results = health.check_all()
        for r in results:
            if r.status != CredentialStatus.OK:
                print(f"WARNING: {r.provider} credential {r.status}: {r.detail}")
    """

    def __init__(self, custom_map: dict[str, tuple[str, str | None]] | None = None) -> None:
        self._creds = {**_CREDENTIALS, **(custom_map or {})}

    def check(self, provider: str) -> CredentialResult:
        """Check the credential for one provider."""
        if provider not in self._creds:
            return CredentialResult(
                provider=provider,
                status=CredentialStatus.UNKNOWN,
                env_var="",
                detail=f"No known env var for {provider!r}",
            )
        env_var, pattern = self._creds[provider]
        value = os.environ.get(env_var, "")

        if not value:
            return CredentialResult(
                provider=provider,
                status=CredentialStatus.MISSING,
                env_var=env_var,
                detail=f"{env_var} is not set",
            )

        if pattern and not re.match(pattern, value):
            return CredentialResult(
                provider=provider,
                status=CredentialStatus.INVALID,
                env_var=env_var,
                detail=f"{env_var} does not match expected format",
            )

        return CredentialResult(
            provider=provider,
            status=CredentialStatus.OK,
            env_var=env_var,
        )

    def check_all(self) -> list[CredentialResult]:
        return [self.check(p) for p in self._creds]

    def check_providers(self, providers: list[str]) -> list[CredentialResult]:
        return [self.check(p) for p in providers]

    def healthy_providers(self) -> list[str]:
        """Return providers with valid credentials."""
        return [r.provider for r in self.check_all() if r.status == CredentialStatus.OK]

    def summary(self) -> dict[str, Any]:
        results = self.check_all()
        return {
            "total": len(results),
            "ok": sum(1 for r in results if r.status == CredentialStatus.OK),
            "missing": sum(1 for r in results if r.status == CredentialStatus.MISSING),
            "invalid": sum(1 for r in results if r.status == CredentialStatus.INVALID),
            "unknown": sum(1 for r in results if r.status == CredentialStatus.UNKNOWN),
        }
