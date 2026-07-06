"""Quarto adapter stub (deferred; graceful missing-tool behavior)."""

from __future__ import annotations

import shutil

QUARTO_SETUP = (
    "Quarto export is deferred in the MVP. Install Quarto from https://quarto.org/docs/get-started/ "
    "when project-level Quarto rendering is enabled."
)


def quarto_available() -> bool:
    return shutil.which("quarto") is not None


def render_with_quarto(*_args, **_kwargs) -> dict[str, str]:
    if quarto_available():
        return {
            "status": "deferred",
            "message": "Quarto is installed but project export is not wired in the MVP slice.",
        }
    return {"status": "missing", "setup_instructions": QUARTO_SETUP}
