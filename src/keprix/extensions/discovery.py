"""Extension discovery via Python entry points (keprix.extensions group)."""

from __future__ import annotations

import importlib.metadata
import logging
from typing import Any

from .base import KeprixExtension

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "keprix.extensions"


class ExtensionConflictError(Exception):
    """Raised when two extensions share the same name."""


class ExtensionDiscovery:
    """Discover and validate Keprix extensions from installed packages.

    Extensions advertise themselves via pyproject.toml entry points::

        [project.entry-points."keprix.extensions"]
        abbis = "abbis.extension:AbbiSExtension"

    This class finds all such entry points, loads the class, instantiates it,
    runs a compatibility check, and returns the healthy extensions.

    Usage::

        discovery = ExtensionDiscovery()
        extensions = discovery.discover()
        discovery.validate_no_conflicts(extensions)
    """

    def discover(self, skip_incompatible: bool = True) -> list[KeprixExtension]:
        """Return all compatible extensions found via entry points."""
        extensions: list[KeprixExtension] = []

        try:
            entry_points = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
        except Exception as exc:
            logger.error("Failed to enumerate entry points: %s", exc)
            return []

        for ep in entry_points:
            try:
                ext_class = ep.load()
                ext: KeprixExtension = ext_class()
            except Exception as exc:
                logger.error("Failed to load extension %s: %s", ep.name, exc)
                continue

            compat = ext.check_compatibility()
            if not compat.compatible:
                if skip_incompatible:
                    logger.warning(
                        "Extension %r incompatible, skipping: %s",
                        ext.name, compat.reason,
                    )
                    continue
                else:
                    raise RuntimeError(
                        f"Extension {ext.name!r} is incompatible: {compat.reason}"
                    )

            extensions.append(ext)
            logger.info("Loaded extension: %s v%s", ext.name, ext.version)

        return extensions

    def validate_no_conflicts(self, extensions: list[KeprixExtension]) -> None:
        """Raise ExtensionConflictError if two extensions share a name."""
        names = [e.name for e in extensions]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ExtensionConflictError(
                f"Duplicate extension names registered: {sorted(duplicates)}"
            )

    def discover_and_validate(self) -> list[KeprixExtension]:
        """Discover, check compatibility, and validate for conflicts."""
        extensions = self.discover()
        self.validate_no_conflicts(extensions)
        return extensions
