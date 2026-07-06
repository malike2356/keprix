"""Playbook localization metadata helpers."""

from __future__ import annotations

from typing import Any

from keprix.backend.playbook.meta import PlaybookLocalizationMeta
from keprix.products.assets import load_product_playbook_localization


def get_playbook_localization_meta(playbook_id: str) -> PlaybookLocalizationMeta | None:
    return load_product_playbook_localization().get(playbook_id)


class _LazyPlaybookMeta:
    """Resolve playbook metadata from product config on first attribute access."""

    _cached: PlaybookLocalizationMeta | None = None

    def _resolve(self) -> PlaybookLocalizationMeta:
        if self._cached is None:
            self._cached = get_playbook_localization_meta("ghana-borehole-advisor") or PlaybookLocalizationMeta(
                playbook_id="ghana-borehole-advisor"
            )
        return self._cached

    def __getattr__(self, item: str) -> Any:
        return getattr(self._resolve(), item)


GHANA_BOREHOLE_PLAYBOOK = _LazyPlaybookMeta()
