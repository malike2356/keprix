"""Input validation at API boundaries."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse


class ValidationError(ValueError):
    """Raised when input fails validation."""


_SHELL_METACHAR_RE = re.compile(r"[;&|`$<>(){}[\]\\!#*?~]")


class InputValidator:
    MAX_STRING_LENGTH = 65536
    MAX_ARRAY_LENGTH = 1000
    MAX_NESTED_DEPTH = 10

    def validate_string(self, value: str, field_name: str, max_length: int | None = None) -> str:
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        if "\x00" in value:
            raise ValidationError(f"{field_name} contains null bytes")
        limit = max_length if max_length is not None else self.MAX_STRING_LENGTH
        if len(value) > limit:
            raise ValidationError(f"{field_name} exceeds maximum length of {limit}")
        return value.strip()

    def validate_url(
        self,
        value: str,
        field_name: str,
        allowed_schemes: list[str] | None = None,
    ) -> str:
        cleaned = self.validate_string(value, field_name)
        parsed = urlparse(cleaned)
        schemes = allowed_schemes or ["https", "http"]
        if parsed.scheme not in schemes:
            raise ValidationError(f"{field_name} must use one of: {', '.join(schemes)}")
        if not parsed.netloc:
            raise ValidationError(f"{field_name} is not a valid URL")
        return cleaned

    def validate_path(self, value: str, field_name: str, base_dir: str) -> str:
        cleaned = self.validate_string(value, field_name)
        base = Path(base_dir).expanduser().resolve()
        candidate = (base / cleaned).resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise ValidationError(f"{field_name} resolves outside allowed directory") from exc
        return str(candidate)

    def validate_command_arg(self, value: str, field_name: str) -> str:
        cleaned = self.validate_string(value, field_name, max_length=4096)
        if _SHELL_METACHAR_RE.search(cleaned):
            raise ValidationError(f"{field_name} contains shell metacharacters")
        return cleaned

    def validate_nested(self, value: object, field_name: str, depth: int = 0) -> object:
        if depth > self.MAX_NESTED_DEPTH:
            raise ValidationError(f"{field_name} exceeds maximum nesting depth")
        if isinstance(value, str):
            return self.validate_string(value, field_name)
        if isinstance(value, list):
            if len(value) > self.MAX_ARRAY_LENGTH:
                raise ValidationError(f"{field_name} exceeds maximum array length")
            return [self.validate_nested(item, f"{field_name}[{index}]", depth + 1) for index, item in enumerate(value)]
        if isinstance(value, dict):
            if len(value) > self.MAX_ARRAY_LENGTH:
                raise ValidationError(f"{field_name} exceeds maximum object size")
            return {
                str(key): self.validate_nested(item, f"{field_name}.{key}", depth + 1)
                for key, item in value.items()
            }
        return value


default_validator = InputValidator()
