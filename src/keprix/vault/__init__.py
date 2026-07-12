"""Universal markdown vault provider."""

from keprix.vault.capture import auto_capture_enabled, capture_conversation, ensure_default_vault
from keprix.vault.config import VaultConfig, get_vault_config, save_vault_config
from keprix.vault.local_folder import LocalFolderVault
from keprix.vault.provider import VaultFile, VaultProvider

__all__ = [
    "LocalFolderVault",
    "VaultConfig",
    "VaultFile",
    "VaultProvider",
    "auto_capture_enabled",
    "capture_conversation",
    "ensure_default_vault",
    "get_vault_config",
    "save_vault_config",
]
