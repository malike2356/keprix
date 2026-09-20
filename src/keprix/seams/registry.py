"""Seam provider registry (one active Provider per seam)."""

from __future__ import annotations

import threading
from typing import Any

from keprix.seams.errors import SeamError, SeamNotFoundError
from keprix.seams.ids import SEAM_IDS, SeamId

_lock = threading.RLock()
_REGISTRY: SeamRegistry | None = None


class SeamRegistry:
    """Register and activate Providers behind seam Definitions.

    Does not replace ``tools.registry``; it names which Provider backs each
    capability so related tools can move together when the active Provider swaps.
    """

    def __init__(self) -> None:
        self._providers: dict[SeamId, dict[str, Any]] = {seam: {} for seam in SEAM_IDS}
        self._active: dict[SeamId, str | None] = {seam: None for seam in SEAM_IDS}

    def register(
        self,
        seam: SeamId,
        provider: Any,
        *,
        make_active: bool = False,
    ) -> None:
        if seam not in SEAM_IDS:
            raise SeamNotFoundError(f"Unknown seam: {seam}")
        provider_id = getattr(provider, "provider_id", None)
        if not provider_id or not isinstance(provider_id, str):
            raise SeamError("Provider must expose a non-empty provider_id str")
        with _lock:
            self._providers[seam][provider_id] = provider
            if make_active or self._active[seam] is None:
                self._active[seam] = provider_id

    def set_active(self, seam: SeamId, provider_id: str) -> Any:
        with _lock:
            if seam not in SEAM_IDS:
                raise SeamNotFoundError(f"Unknown seam: {seam}")
            provider = self._providers[seam].get(provider_id)
            if provider is None:
                raise SeamNotFoundError(
                    f"No provider {provider_id!r} registered for seam {seam}"
                )
            self._active[seam] = provider_id
            return provider

    def get(self, seam: SeamId) -> Any:
        with _lock:
            if seam not in SEAM_IDS:
                raise SeamNotFoundError(f"Unknown seam: {seam}")
            active_id = self._active[seam]
            if active_id is None:
                raise SeamNotFoundError(f"No active provider for seam {seam}")
            provider = self._providers[seam].get(active_id)
            if provider is None:
                raise SeamNotFoundError(
                    f"Active provider {active_id!r} missing for seam {seam}"
                )
            return provider

    def active_id(self, seam: SeamId) -> str | None:
        with _lock:
            return self._active.get(seam)

    def unregister(self, seam: SeamId, provider_id: str) -> bool:
        """Remove a Provider. If it was active, activate another or clear.

        Returns True when the Provider existed. Prefer restoring a default
        ``*.local`` / ``policy:*.local`` / ``*.default`` id when present.
        """
        with _lock:
            if seam not in SEAM_IDS:
                raise SeamNotFoundError(f"Unknown seam: {seam}")
            providers = self._providers[seam]
            if provider_id not in providers:
                return False
            del providers[provider_id]
            if self._active[seam] == provider_id:
                fallback = None
                for candidate in (
                    f"policy:{seam}.local",
                    f"{seam}.local",
                    f"{seam}.default",
                    f"policy:{seam}.default",
                ):
                    if candidate in providers:
                        fallback = candidate
                        break
                if fallback is None and providers:
                    fallback = sorted(providers.keys())[0]
                self._active[seam] = fallback
            return True

    def list_providers(self, seam: SeamId) -> list[str]:
        with _lock:
            if seam not in SEAM_IDS:
                raise SeamNotFoundError(f"Unknown seam: {seam}")
            return sorted(self._providers[seam].keys())

    def snapshot(self) -> dict[str, Any]:
        with _lock:
            return {
                seam: {
                    "active": self._active[seam],
                    "providers": sorted(self._providers[seam].keys()),
                }
                for seam in SEAM_IDS
            }

    def clear(self) -> None:
        with _lock:
            for seam in SEAM_IDS:
                self._providers[seam].clear()
                self._active[seam] = None


def get_seam_registry() -> SeamRegistry:
    global _REGISTRY
    with _lock:
        if _REGISTRY is None:
            _REGISTRY = SeamRegistry()
        return _REGISTRY


def _reset_registry_for_tests() -> SeamRegistry:
    global _REGISTRY
    with _lock:
        _REGISTRY = SeamRegistry()
        return _REGISTRY
