"""Vault starter pack discovery."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class VaultPack:
    id: str
    name: str
    version: str
    description: str
    path: str
    docs_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _repo_optional_skills_root() -> Path:
    return Path(__file__).resolve().parents[1] / "optional-skills"


def obsidian_starter_pack_path() -> Path:
    return _repo_optional_skills_root() / "productivity" / "obsidian-vault-starter"


def list_vault_packs() -> list[VaultPack]:
    path = obsidian_starter_pack_path()
    packs: list[VaultPack] = []
    if (path / "pack" / "KEPRIX.md").is_file():
        packs.append(
            VaultPack(
                id="obsidian-starter",
                name="Obsidian vault starter",
                version="1.0.0",
                description="Folder conventions, templates, and KEPRIX.md bootstrap for an Obsidian-compatible vault.",
                path=str(path),
                docs_path="docs/features/obsidian-vault-starter-pack.md",
            )
        )
    return packs


def get_vault_pack(pack_id: str) -> VaultPack:
    normalized = pack_id.strip().lower()
    aliases = {"obsidian-vault-starter": "obsidian-starter", "obsidian": "obsidian-starter"}
    normalized = aliases.get(normalized, normalized)
    for pack in list_vault_packs():
        if pack.id == normalized:
            return pack
    raise ValueError(f"Unknown vault pack: {pack_id}")
