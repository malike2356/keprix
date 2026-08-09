"""Feature flags for Document Vault (Prompt 645)."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DocumentVaultFlags:
    enabled: bool = False
    migrate: bool = False
    cutover: bool = False
    host_fs_bridge: bool = False
    google_sync: bool = False
    google_shared_drives: bool = False

    def as_env_map(self) -> dict[str, bool]:
        return {
            "KEPRIX_DOCUMENT_VAULT_ENABLED": self.enabled,
            "KEPRIX_DOCUMENT_VAULT_MIGRATE": self.migrate,
            "KEPRIX_DOCUMENT_VAULT_CUTOVER": self.cutover,
            "KEPRIX_DOCUMENT_VAULT_HOST_FS_BRIDGE": self.host_fs_bridge,
            "KEPRIX_DOCUMENT_VAULT_GOOGLE_SYNC": self.google_sync,
            "KEPRIX_DOCUMENT_VAULT_GOOGLE_SHARED_DRIVES": False,
        }


def load_flags() -> DocumentVaultFlags:
    """Load flags. Host FS bridge and Shared Drives stay forced off."""
    return DocumentVaultFlags(
        enabled=_env_bool("KEPRIX_DOCUMENT_VAULT_ENABLED", False),
        migrate=_env_bool("KEPRIX_DOCUMENT_VAULT_MIGRATE", False),
        cutover=_env_bool("KEPRIX_DOCUMENT_VAULT_CUTOVER", False),
        host_fs_bridge=False,
        google_sync=_env_bool("KEPRIX_DOCUMENT_VAULT_GOOGLE_SYNC", False),
        google_shared_drives=False,
    )


def flags_dict() -> dict[str, bool]:
    return asdict(load_flags())
