"""Channel Document Vault package (Prompt 651).

Reusable attachment and command contract for Telegram and the enabled
channel matrix. Trusted identity binding only; never infer workspace from
message content, filenames, or model arguments.
"""

from __future__ import annotations

from keprix.document_vault.channel.binding import (
    bind_channel_identity,
    resolve_channel_binding,
    revoke_channel_binding,
)
from keprix.document_vault.channel.commands import handle_vault_channel_command
from keprix.document_vault.channel.contract import (
    CHANNEL_MATRIX,
    ChannelAttachment,
    channel_supports_files,
)
from keprix.document_vault.channel.export_delivery import plan_export_delivery
from keprix.document_vault.channel.import_pipeline import import_channel_attachment

__all__ = [
    "CHANNEL_MATRIX",
    "ChannelAttachment",
    "bind_channel_identity",
    "channel_supports_files",
    "handle_vault_channel_command",
    "import_channel_attachment",
    "plan_export_delivery",
    "resolve_channel_binding",
    "revoke_channel_binding",
]
