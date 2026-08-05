"""Strip sensitive credential values before TTS synthesis."""

from __future__ import annotations

import re

from keprix.channels.channel_requirements import get_sensitive_field_keys as channel_sensitive_keys

_REDACTED = "[redacted]"
_SENSITIVE_HINT = (
    "If you prefer, type this next value instead of saying it aloud."
)


def get_all_sensitive_field_keys() -> set[str]:
    keys = set(channel_sensitive_keys())
    try:
        from keprix.configure.provider_requirements import get_sensitive_provider_field_keys

        keys |= get_sensitive_provider_field_keys()
    except Exception:
        pass
    try:
        from keprix.configure.scout_config_service import get_sensitive_scout_field_keys

        keys |= get_sensitive_scout_field_keys()
    except Exception:
        pass
    try:
        from keprix.configure.integration_requirements import get_sensitive_integration_field_keys

        keys |= get_sensitive_integration_field_keys()
    except Exception:
        pass
    return keys


def scrub_secrets_for_speech(text: str, *, extra_values: list[str] | None = None) -> str:
    """Remove known secret-like substrings and label:value pairs before TTS."""
    if not text:
        return text

    out = text
    for value in extra_values or []:
        if value and len(value) >= 6 and value in out:
            out = out.replace(value, _REDACTED)

    keys = sorted(get_all_sensitive_field_keys(), key=len, reverse=True)
    for key in keys:
        pattern = re.compile(
            rf"(?i)\b{re.escape(key)}\b\s*[:=]\s*([^\s,;]+)",
        )
        out = pattern.sub(lambda m: f"{key}: {_REDACTED}", out)

    out = re.sub(r"\b\d{8,12}:[A-Za-z0-9_-]{20,}\b", _REDACTED, out)
    out = re.sub(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", _REDACTED, out)
    out = re.sub(r"\bxapp-[A-Za-z0-9-]{10,}\b", _REDACTED, out)
    out = re.sub(r"\bsk-[A-Za-z0-9_-]{16,}\b", _REDACTED, out)
    out = re.sub(r"\bsk-ant-[A-Za-z0-9_-]{16,}\b", _REDACTED, out)

    return out


def sensitive_field_warning(*, field_label: str | None = None) -> str:
    if field_label:
        return f"I need your {field_label} next. {_SENSITIVE_HINT}"
    return _SENSITIVE_HINT
