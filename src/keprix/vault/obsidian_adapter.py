"""Obsidian-compatible vault provider."""

from __future__ import annotations

from pathlib import Path

from keprix.vault.local_folder import LocalFolderVault


class ObsidianVault(LocalFolderVault):
    """Obsidian vaults are markdown folders with app metadata excluded."""

    def __init__(self, root_path: str | Path) -> None:
        super().__init__(root_path)
