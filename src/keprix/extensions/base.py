"""KeprixExtension base class: contract for all products built on Keprix."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompatibilityResult:
    compatible: bool
    reason: str = ""


class KeprixExtension(ABC):
    """Base class for any product built on Keprix.

    Products subclass this and are discovered automatically via Python
    entry points (group ``keprix.extensions``). Keprix loads them at
    startup, checks compatibility, and registers their routes and tools.

    Minimal product implementation::

        class MyExtension(KeprixExtension):
            name = "myproduct"
            display_name = "My Product"
            version = "1.0.0"
            keprix_min_version = "0.3.0"

            async def on_startup(self) -> None:
                pass

            async def on_shutdown(self) -> None:
                pass
    """

    # Identity
    name: str = ""
    display_name: str = ""
    version: str = "0.0.0"
    keprix_min_version: str = "0.3.0"

    # What this extension provides
    routes: list = []
    domain_tools: list = []
    domain_packs: list = []
    personas: list = []
    skill_packs: list = []
    ui_components: list = []

    # What this extension requires from Keprix
    required_features: list[str] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    async def on_startup(self) -> None:
        """Called once when Keprix starts and the extension is loaded."""

    @abstractmethod
    async def on_shutdown(self) -> None:
        """Called once when Keprix is shutting down."""

    # ------------------------------------------------------------------
    # Compatibility check
    # ------------------------------------------------------------------

    def check_compatibility(self) -> CompatibilityResult:
        """Return whether this extension is compatible with the running Keprix."""
        from .compatibility import check_version_compatible, check_features_available

        version_ok, reason = check_version_compatible(self.keprix_min_version)
        if not version_ok:
            return CompatibilityResult(compatible=False, reason=reason)

        missing = check_features_available(self.required_features)
        if missing:
            return CompatibilityResult(
                compatible=False,
                reason=f"Missing required Keprix features: {missing}",
            )

        return CompatibilityResult(compatible=True)

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "version": self.version,
            "keprix_min_version": self.keprix_min_version,
            "required_features": self.required_features,
            "provides": {
                "routes": len(self.routes),
                "domain_tools": len(self.domain_tools),
                "personas": len(self.personas),
                "ui_components": len(self.ui_components),
            },
        }
