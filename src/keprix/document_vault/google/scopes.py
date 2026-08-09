"""Google Drive scopes and sync modes for Document Vault (Prompt 649)."""

from __future__ import annotations

from typing import Literal

SyncMode = Literal["outbound_only", "inbound_only", "two_way"]

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
DRIVE_FULL_SCOPE = "https://www.googleapis.com/auth/drive"
DRIVE_METADATA_READONLY = "https://www.googleapis.com/auth/drive.metadata.readonly"
USERINFO_EMAIL = "https://www.googleapis.com/auth/userinfo.email"
OPENID = "openid"

# Prefer drive.file for app-created / user-selected files.
MODE_SCOPES: dict[SyncMode, tuple[str, ...]] = {
    "outbound_only": (OPENID, USERINFO_EMAIL, DRIVE_FILE_SCOPE),
    "inbound_only": (OPENID, USERINFO_EMAIL, DRIVE_FULL_SCOPE),
    "two_way": (OPENID, USERINFO_EMAIL, DRIVE_FULL_SCOPE),
}

MODE_CONSENT: dict[SyncMode, str] = {
    "outbound_only": (
        "Outbound-only sync uses drive.file so Keprix can create and update files "
        "it owns or that you explicitly select. It cannot browse your full Drive."
    ),
    "inbound_only": (
        "Inbound-only sync needs full Drive read access to follow changes under "
        "your selected root. Keprix will not push local edits to Google."
    ),
    "two_way": (
        "Two-way sync needs full Drive access under your selected root so Keprix "
        "can pull Google changes and push local vault edits. This is a privileged grant."
    ),
}


def scopes_for_mode(mode: str) -> list[str]:
    key: SyncMode = mode if mode in MODE_SCOPES else "outbound_only"  # type: ignore[assignment]
    if mode not in MODE_SCOPES:
        key = "outbound_only"
    return list(MODE_SCOPES[key])


def mode_requires_full_drive(mode: str) -> bool:
    return mode in {"inbound_only", "two_way"}


def consent_copy(mode: str) -> str:
    return MODE_CONSENT.get(mode, MODE_CONSENT["outbound_only"])  # type: ignore[arg-type]


def validate_mode(mode: str) -> SyncMode:
    if mode not in MODE_SCOPES:
        raise ValueError(f"unsupported sync mode: {mode}")
    return mode  # type: ignore[return-value]


__all__ = [
    "DRIVE_FILE_SCOPE",
    "DRIVE_FULL_SCOPE",
    "MODE_CONSENT",
    "MODE_SCOPES",
    "SyncMode",
    "consent_copy",
    "mode_requires_full_drive",
    "scopes_for_mode",
    "validate_mode",
]
