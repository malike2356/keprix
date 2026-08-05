"""FastAPI dependencies for edition-gated features."""

from __future__ import annotations

from keprix.licensing.edition import FEATURE_MATRIX, current_edition, feature_enabled, require_enterprise


def enterprise_feature(feature: str):
    def _dependency() -> None:
        require_enterprise(feature)

    return _dependency


def get_edition_info() -> dict:
    edition = current_edition()
    return {
        "edition": edition,
        "features": {feature: feature_enabled(feature) for feature in FEATURE_MATRIX},
    }
