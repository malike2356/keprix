"""Contact sync connector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class SyncResult:
    added: int = 0
    updated: int = 0
    skipped: int = 0
    sync_token: str | None = None
    error: str | None = None


class ContactSyncConnector(ABC):
    @abstractmethod
    async def full_sync(self, source: dict[str, Any]) -> SyncResult:
        raise NotImplementedError

    @abstractmethod
    async def delta_sync(self, source: dict[str, Any]) -> SyncResult:
        raise NotImplementedError

    async def get_auth_url(self) -> str:
        raise NotImplementedError

    async def exchange_code(self, code: str) -> dict[str, Any]:
        raise NotImplementedError
