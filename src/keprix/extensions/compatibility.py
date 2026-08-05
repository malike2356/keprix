"""Version compatibility checking for Keprix extensions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import total_ordering

logger = logging.getLogger(__name__)

# Kept as a module-level constant so it can be overridden in tests.
KEPRIX_VERSION = "0.3.0"

# Features available in this Keprix version.
_AVAILABLE_FEATURES = frozenset({
    "billing",
    "governance",
    "providers",
    "notion",
    "extensions",
    "observability",
    "a2a",
    "evals",
    "compliance",
    "resilience",
})


@total_ordering
@dataclass
class _Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version_str: str) -> "_Version":
        parts = str(version_str).split(".")
        try:
            return cls(
                major=int(parts[0]) if len(parts) > 0 else 0,
                minor=int(parts[1]) if len(parts) > 1 else 0,
                patch=int(parts[2]) if len(parts) > 2 else 0,
            )
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Invalid version string: {version_str!r}") from exc

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __lt__(self, other: "_Version") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def check_version_compatible(min_version: str) -> tuple[bool, str]:
    """Return (ok, reason) indicating whether the running Keprix satisfies the minimum.

    An extension that requires >=0.3.0 will be rejected if running on 0.2.x.
    It will be accepted on 0.3.x, 0.4.x, etc.
    """
    try:
        current = _Version.parse(KEPRIX_VERSION)
        minimum = _Version.parse(min_version)
    except ValueError as exc:
        return False, str(exc)

    if current < minimum:
        return (
            False,
            f"Extension requires Keprix >= {minimum}, running {current}.",
        )
    return True, ""


def check_features_available(required: list[str]) -> list[str]:
    """Return the list of required features that are NOT available."""
    return [f for f in required if f not in _AVAILABLE_FEATURES]


def features_available() -> frozenset[str]:
    return _AVAILABLE_FEATURES
