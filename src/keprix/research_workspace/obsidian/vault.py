"""Obsidian vault registration and path policy."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from keprix.compat import StrEnum
from pathlib import Path
from typing import Any

from keprix.research_workspace.errors import ResearchWorkspaceError, VaultPathError


class SyncMode(StrEnum):
    READ_ONLY = "read-only"
    WRITE_DRAFT = "write-draft"
    WRITE_APPROVED = "write-approved"


@dataclass
class VaultConfig:
    vault_id: str
    name: str
    local_path: str
    allowed_folders: list[str] = field(default_factory=lambda: ["."])
    excluded_folders: list[str] = field(default_factory=lambda: [".obsidian", ".trash"])
    attachment_folder: str = "attachments"
    template_folder: str = "templates"
    sync_mode: str = SyncMode.WRITE_DRAFT
    allow_external_path: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VaultConfig:
        return cls(
            vault_id=str(data["vault_id"]),
            name=str(data["name"]),
            local_path=str(data["local_path"]),
            allowed_folders=list(data.get("allowed_folders") or ["."]),
            excluded_folders=list(data.get("excluded_folders") or [".obsidian", ".trash"]),
            attachment_folder=str(data.get("attachment_folder") or "attachments"),
            template_folder=str(data.get("template_folder") or "templates"),
            sync_mode=str(data.get("sync_mode") or SyncMode.WRITE_DRAFT),
            allow_external_path=bool(data.get("allow_external_path")),
        )


class VaultRegistry:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.config_path = workspace_root / "obsidian_vaults.json"
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def list_vaults(self) -> list[VaultConfig]:
        return [VaultConfig.from_dict(item) for item in self._load()]

    def get_vault(self, vault_id: str) -> VaultConfig | None:
        for vault in self.list_vaults():
            if vault.vault_id == vault_id:
                return vault
        return None

    def register(
        self,
        *,
        name: str,
        local_path: str,
        allowed_folders: list[str] | None = None,
        excluded_folders: list[str] | None = None,
        attachment_folder: str = "attachments",
        template_folder: str = "templates",
        sync_mode: str = SyncMode.WRITE_DRAFT,
        allow_external_path: bool = False,
    ) -> VaultConfig:
        resolved = validate_vault_path(
            local_path,
            workspace_root=self.workspace_root,
            allow_external=allow_external_path,
        )
        vault = VaultConfig(
            vault_id=f"vault-{uuid.uuid4().hex[:10]}",
            name=name,
            local_path=str(resolved),
            allowed_folders=allowed_folders or ["."],
            excluded_folders=excluded_folders or [".obsidian", ".trash"],
            attachment_folder=attachment_folder,
            template_folder=template_folder,
            sync_mode=sync_mode,
            allow_external_path=allow_external_path,
        )
        items = self._load()
        items.append(vault.to_dict())
        self._save(items)
        resolved.mkdir(parents=True, exist_ok=True)
        return vault

    def _load(self) -> list[dict[str, Any]]:
        if not self.config_path.exists():
            return []
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def _save(self, items: list[dict[str, Any]]) -> None:
        self.config_path.write_text(json.dumps(items, indent=2), encoding="utf-8")


def validate_vault_path(path: str | Path, *, workspace_root: Path, allow_external: bool) -> Path:
    resolved = Path(path).expanduser().resolve()
    workspace_resolved = workspace_root.resolve()
    inside_workspace = resolved == workspace_resolved or workspace_resolved in resolved.parents
    if not inside_workspace and not allow_external:
        raise VaultPathError(
            "Vault path must be inside workspace storage or allow_external_path must be true"
        )
    return resolved


def is_path_allowed(rel_path: Path, vault: VaultConfig) -> bool:
    parts = rel_path.parts
    for excluded in vault.excluded_folders:
        excluded_norm = excluded.strip("./")
        if excluded_norm and excluded_norm in parts:
            return False
    if vault.allowed_folders == ["."]:
        return True
    rel = rel_path.as_posix().lstrip("./")
    for allowed in vault.allowed_folders:
        allowed_norm = allowed.strip("./")
        if allowed_norm == "." or rel == allowed_norm or rel.startswith(f"{allowed_norm}/"):
            return True
    return False


def should_skip_path(path: Path, vault_root: Path, vault: VaultConfig) -> bool:
    rel = path.relative_to(vault_root)
    if not is_path_allowed(rel, vault):
        return True
    gitignore = vault_root / ".gitignore"
    if gitignore.exists():
        patterns = [
            line.strip()
            for line in gitignore.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        rel_posix = rel.as_posix()
        for pattern in patterns:
            if pattern.endswith("/") and rel_posix.startswith(pattern.rstrip("/")):
                return True
            if pattern == rel.name or pattern == rel_posix:
                return True
    return False
