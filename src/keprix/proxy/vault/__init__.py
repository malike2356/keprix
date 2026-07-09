"""Vault provider trait and backends for per-request credential fetch."""

from __future__ import annotations

import json
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from keprix.proxy.paths import local_vault_path
from keprix.proxy.secret import Secret


class VaultProvider(ABC):
    name: str

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch(self, secret_ref: str) -> Secret:
        raise NotImplementedError


class LocalFileVault(VaultProvider):
    """Development and test vault stored under KEPRIX_HOME."""

    name = "keychain"

    def is_available(self) -> bool:
        return True

    def fetch(self, secret_ref: str) -> Secret:
        path = local_vault_path()
        if not path.is_file():
            raise KeyError(f"Local vault missing at {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        secrets = data.get("secrets", {})
        if secret_ref not in secrets:
            raise KeyError(f"Secret {secret_ref!r} not found in local vault")
        return Secret(str(secrets[secret_ref]))


class BitwardenCliVault(VaultProvider):
    name = "bitwarden"

    def is_available(self) -> bool:
        if shutil_which("bws"):
            return bool(os.getenv("BWS_ACCESS_TOKEN") or os.getenv("BITWARDEN_CLIENT_SECRET"))
        return shutil_which("bw") is not None

    def fetch(self, secret_ref: str) -> Secret:
        if shutil_which("bws"):
            token = os.getenv("BWS_ACCESS_TOKEN") or os.getenv("BITWARDEN_CLIENT_SECRET", "")
            project = os.getenv("BITWARDEN_PROJECT_ID", "")
            if not token or not project:
                raise RuntimeError("Set BWS_ACCESS_TOKEN and BITWARDEN_PROJECT_ID for Bitwarden")
            proc = subprocess.run(
                ["bws", "secret", "list", project, "--output", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env={**os.environ, "BWS_ACCESS_TOKEN": token},
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or "bws secret list failed")
            rows = json.loads(proc.stdout)
            for row in rows:
                if not isinstance(row, dict):
                    continue
                key = str(row.get("key") or row.get("id") or "")
                if key == secret_ref:
                    return Secret(str(row.get("value") or ""))
            raise KeyError(f"Bitwarden secret {secret_ref!r} not found")

        proc = subprocess.run(
            ["bw", "get", "password", secret_ref],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "bw get failed")
        return Secret(proc.stdout.strip())


class OnePasswordCliVault(VaultProvider):
    name = "onepassword"

    def is_available(self) -> bool:
        return shutil_which("op") is not None

    def fetch(self, secret_ref: str) -> Secret:
        # secret_ref format: op://vault/item/field or item title
        target = secret_ref if secret_ref.startswith("op://") else f"op://Private/{secret_ref}"
        proc = subprocess.run(
            ["op", "read", target],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "op read failed")
        return Secret(proc.stdout.strip())


def shutil_which(name: str) -> str | None:
    from shutil import which

    return which(name)


def get_vault_provider(name: str) -> VaultProvider:
    providers: dict[str, VaultProvider] = {
        "keychain": LocalFileVault(),
        "local": LocalFileVault(),
        "bitwarden": BitwardenCliVault(),
        "onepassword": OnePasswordCliVault(),
    }
    provider = providers.get(name.lower())
    if provider is None:
        raise ValueError(f"Unknown vault provider: {name}")
    return provider
