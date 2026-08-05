"""Tests for extensions/discovery.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from keprix.extensions.base import CompatibilityResult, KeprixExtension
from keprix.extensions.discovery import ExtensionConflictError, ExtensionDiscovery


class _GoodExt(KeprixExtension):
    name = "good"
    display_name = "Good Extension"
    version = "1.0.0"
    keprix_min_version = "0.3.0"

    async def on_startup(self) -> None:
        pass

    async def on_shutdown(self) -> None:
        pass


class _BadExt(KeprixExtension):
    name = "bad"
    display_name = "Bad Extension"
    version = "1.0.0"
    keprix_min_version = "99.0.0"  # requires a future version

    async def on_startup(self) -> None:
        pass

    async def on_shutdown(self) -> None:
        pass


@pytest.fixture
def discovery():
    return ExtensionDiscovery()


def test_discover_no_entry_points_returns_empty(discovery):
    with patch("importlib.metadata.entry_points", return_value=[]):
        result = discovery.discover()
    assert result == []


def test_discover_loads_compatible_extension(discovery):
    ep = MagicMock()
    ep.name = "good"
    ep.load.return_value = _GoodExt

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        result = discovery.discover()

    assert len(result) == 1
    assert result[0].name == "good"


def test_discover_skips_incompatible_by_default(discovery):
    ep = MagicMock()
    ep.name = "bad"
    ep.load.return_value = _BadExt

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        result = discovery.discover(skip_incompatible=True)

    assert result == []


def test_discover_raises_incompatible_in_strict_mode(discovery):
    ep = MagicMock()
    ep.name = "bad"
    ep.load.return_value = _BadExt

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        with pytest.raises(RuntimeError, match="incompatible"):
            discovery.discover(skip_incompatible=False)


def test_discover_skips_load_error(discovery):
    ep = MagicMock()
    ep.name = "broken"
    ep.load.side_effect = ImportError("module not found")

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        result = discovery.discover()

    assert result == []


def test_validate_no_conflicts_passes_unique(discovery):
    exts = [_GoodExt()]
    discovery.validate_no_conflicts(exts)  # should not raise


def test_validate_no_conflicts_raises_on_duplicate(discovery):
    exts = [_GoodExt(), _GoodExt()]  # two extensions with same name "good"
    with pytest.raises(ExtensionConflictError, match="good"):
        discovery.validate_no_conflicts(exts)
