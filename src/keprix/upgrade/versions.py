"""Version comparison helpers for the upgrade system."""

from __future__ import annotations


def version_tuple(v: str) -> tuple[int, ...]:
    """Parse a dotted version string into a comparable tuple."""
    parts: list[int] = []
    for segment in str(v).split("."):
        # Strip pre-release suffixes like "0.7.0-rc1" -> compare on numeric prefix only.
        numeric = segment.split("-")[0]
        parts.append(int(numeric))
    return tuple(parts)


def version_lt(a: str, b: str) -> bool:
    return version_tuple(a) < version_tuple(b)


def version_lte(a: str, b: str) -> bool:
    return version_tuple(a) <= version_tuple(b)


def version_gt(a: str, b: str) -> bool:
    return version_tuple(a) > version_tuple(b)


def version_gte(a: str, b: str) -> bool:
    return version_tuple(a) >= version_tuple(b)


def sort_versions(versions: list[str]) -> list[str]:
    """Return versions sorted ascending."""
    return sorted(versions, key=version_tuple)


def versions_between(
    from_version: str,
    to_version: str,
    available_versions: list[str],
) -> list[str]:
    """Return sorted versions strictly after from_version up to and including to_version."""
    return [
        v for v in sort_versions(available_versions)
        if version_gt(v, from_version) and version_lte(v, to_version)
    ]


def latest_version(versions: list[str]) -> str | None:
    """Return the highest version in the list, or None if empty."""
    if not versions:
        return None
    return sort_versions(versions)[-1]
