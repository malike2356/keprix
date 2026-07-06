"""Scout product extension manifest (optional governance provider)."""

from __future__ import annotations

from keprix.extensions.registry import ExtensionManifest

SCOUT_HOMEPAGE = "https://labyrinthscout.com"
SCOUT_API_DEFAULT = "https://api.labyrinthscout.com"


def load_manifest() -> ExtensionManifest:
    return ExtensionManifest(
        name="scout",
        display_name="Scout",
        version="1.0.0",
        homepage=SCOUT_HOMEPAGE,
        governance_provider="scout",
        feature_flags={"audit_stream": True},
    )


MANIFEST = load_manifest()
