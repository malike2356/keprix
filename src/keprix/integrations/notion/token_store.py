"""Secure Notion token storage: reads from env, never logs the value."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_ENV_VAR = "NOTION_INTEGRATION_TOKEN"


class NotionTokenStore:
    """Read the Notion integration token from the environment.

    In development, set ``NOTION_INTEGRATION_TOKEN`` in your .env file.
    In production, inject it via your secrets manager.

    The token is never logged or included in exception messages.
    """

    def __init__(self, env_var: str = _ENV_VAR) -> None:
        self._env_var = env_var

    def get(self) -> str:
        """Return the integration token. Raises ValueError if not set."""
        token = os.environ.get(self._env_var, "")
        if not token:
            raise ValueError(
                f"Notion integration token not configured. "
                f"Set {self._env_var} in your environment."
            )
        return token

    def is_configured(self) -> bool:
        """Return True if the token env var is non-empty."""
        return bool(os.environ.get(self._env_var, ""))

    def is_enabled(self) -> bool:
        """Return True if Notion integration is explicitly enabled."""
        enabled = os.environ.get("KEPRIX_NOTION_ENABLED", "false").lower()
        return enabled in ("1", "true", "yes") and self.is_configured()
