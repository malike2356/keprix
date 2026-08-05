"""Compat shims for Python 3.10 hosts."""

from __future__ import annotations

from enum import Enum

from keprix.compat import UTC, StrEnum, Self, tomllib


def test_strenum_behaves_like_str():
    class Color(StrEnum):
        RED = "red"

    assert Color.RED == "red"
    assert isinstance(Color.RED, str)
    assert issubclass(Color, Enum)


def test_utc_is_timezone_aware():
    from datetime import datetime

    assert datetime.now(UTC).tzinfo is not None


def test_tomllib_loads_minimal():
    data = tomllib.loads('name = "keprix"\n')
    assert data["name"] == "keprix"


def test_self_is_importable():
    assert Self is not None
