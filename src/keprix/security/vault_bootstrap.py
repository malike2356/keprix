"""Bootstrap vault interface (Prompt 08 replaces implementation)."""

from __future__ import annotations

import os


class VaultClient:
    """
    Bootstrap interface. Returns plaintext credentials from environment variables.
    Prompt 08 replaces this with the full AES-256 encrypted vault backend.
    """

    def get(self, key: str) -> str | None:
        return os.environ.get(key)

    def set(self, key: str, value: str) -> None:
        return None

    def delete(self, key: str) -> None:
        return None


vault = VaultClient()
