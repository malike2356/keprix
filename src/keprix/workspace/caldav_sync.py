"""Backward-compatible CalDAV sync entrypoints."""

from __future__ import annotations

from typing import Any

from keprix.workspace.calendar_sync import PROVIDER_PRESETS, sync_caldav

__all__ = ["PROVIDER_PRESETS", "sync_caldav"]
