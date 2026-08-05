"""Python version compatibility shims (3.10+ host support).

Prefer importing StrEnum, UTC, Self, and tomllib from this package when
stdlib symbols are only available on newer CPython releases.
"""

from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python < 3.11
    from enum import Enum

    class StrEnum(str, Enum):
        """Minimal StrEnum backport for Python 3.10."""


try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python < 3.11
    from datetime import timezone

    UTC = timezone.utc


try:
    from typing import Self
except ImportError:  # pragma: no cover - Python < 3.11
    try:
        from typing_extensions import Self
    except ImportError:  # pragma: no cover
        Self = object  # type: ignore[misc,assignment]


try:
    import tomllib
except ImportError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]


__all__ = ["StrEnum", "UTC", "Self", "tomllib"]
