"""Syncthing types for Obsidian vault sync."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

WriterRole = Literal["home", "keprix", "both"]
FolderType = Literal["sendreceive", "sendonly", "receiveonly"]


@dataclass
class SyncthingConfig:
    """GUI-managed Syncthing bridge for the Obsidian vault only.

    Agent-sync (GitHub) owns memory/skills. Syncthing must not point at the
    agent-sync clone. One-writer role maps to Syncthing folder types.
    """

    enabled: bool = False
    # Syncthing REST endpoint (GUI: Actions -> Show ID / Settings -> GUI)
    base_url: str = "http://127.0.0.1:8384"
    # Folder identity inside Syncthing
    folder_id: str = "keprix-obsidian-vault"
    folder_label: str = "Keprix Obsidian Vault"
    # Absolute path synced; default resolved to KEPRIX_HOME/vault when empty
    vault_path: str = ""
    # Path as seen by the Syncthing process (defaults to vault_path).
    # Example: Keprix vault=/home/keprix/.keprix/vault, Syncthing docker=/var/syncthing/vault
    syncthing_path: str = ""
    # Who is allowed to write the vault while Syncthing is enabled
    writer_role: WriterRole = "home"
    # Optional peer device IDs to share the folder with (paste from Syncthing UI)
    device_ids: list[str] = field(default_factory=list)
    # Rescan interval seconds for the vault folder
    rescan_interval_s: int = 60
    last_error: str | None = None
    last_ok_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_CONFIG = SyncthingConfig()

# Paths Syncthing must never sync (agent-sync / secrets)
FORBIDDEN_PATH_MARKERS = (
    "github-agent-sync",
    "/data/github-agent-sync",
    "agent-sync/repo",
)

ONE_WRITER_RULES = {
    "home": {
        "summary": "Home Obsidian is the writer; Keprix/VPS Syncthing folder should be receive-only.",
        "local_folder_type": "receiveonly",
        "peer_folder_type_hint": "sendreceive",
        "keprix_vault_read_only": True,
    },
    "keprix": {
        "summary": "Keprix is the writer (captures); home Obsidian should treat the vault as receive-only / browse.",
        "local_folder_type": "sendreceive",
        "peer_folder_type_hint": "receiveonly",
        "keprix_vault_read_only": False,
    },
    "both": {
        "summary": "WARNING: both sides write. Expect Syncthing conflict copies. Prefer home or keprix.",
        "local_folder_type": "sendreceive",
        "peer_folder_type_hint": "sendreceive",
        "keprix_vault_read_only": False,
    },
}
