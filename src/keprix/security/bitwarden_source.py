"""Read-only Bitwarden Secrets Manager bridge."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class BitwardenSecretSource:
    """Fetch secrets from Bitwarden Secrets Manager when configured."""

    def __init__(self) -> None:
        self.client_id = os.getenv("BITWARDEN_CLIENT_ID", "")
        self.client_secret = os.getenv("BITWARDEN_CLIENT_SECRET", "")
        self.project_id = os.getenv("BITWARDEN_PROJECT_ID", "")
        self.server_url = os.getenv("BITWARDEN_SERVER_URL", "https://vault.bitwarden.com")

    def is_available(self) -> bool:
        return bool(self.client_id and self.client_secret and self.project_id)

    def list_secrets(self) -> dict[str, str]:
        if not self.is_available():
            return {}
        try:
            proc = subprocess.run(
                ["bws", "secret", "list", self.project_id, "--output", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env={
                    **os.environ,
                    "BWS_ACCESS_TOKEN": self.client_secret,
                    "BWS_SERVER_URL": self.server_url,
                },
            )
        except FileNotFoundError:
            logger.warning("Bitwarden CLI (bws) not installed")
            return {}
        if proc.returncode != 0:
            logger.warning("Bitwarden secret list failed: %s", proc.stderr[:200])
            return {}
        try:
            rows = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {}
        secrets: dict[str, str] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key") or row.get("id") or "")
            value = str(row.get("value") or "")
            if key and value:
                secrets[key] = value
        return secrets

    def get_secret(self, name: str) -> str | None:
        return self.list_secrets().get(name)
