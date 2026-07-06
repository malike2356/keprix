"""Gateway slash channel adapters."""

from gateway.slash.discord import handle_discord_slash
from gateway.slash.matrix import handle_matrix_slash
from gateway.slash.slack import handle_slack_slash, verify_slack_signature
from gateway.slash.telegram import handle_telegram_slash, telegram_bot_commands
from gateway.slash.webchat import handle_webchat_slash

__all__ = [
    "handle_discord_slash",
    "handle_matrix_slash",
    "handle_slack_slash",
    "handle_telegram_slash",
    "handle_webchat_slash",
    "telegram_bot_commands",
    "verify_slack_signature",
]
