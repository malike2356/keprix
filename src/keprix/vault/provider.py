"""Vault provider protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VaultFile:
    path: str
    name: str
    is_dir: bool = False
    size: int = 0
    modified_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "name": self.name,
            "is_dir": self.is_dir,
            "size": self.size,
            "modified_at": self.modified_at,
        }


class VaultProvider(ABC):
    @abstractmethod
    async def list_files(self, path: str = "/") -> list[VaultFile]: ...

    @abstractmethod
    async def read_file(self, path: str) -> str: ...

    @abstractmethod
    async def write_file(self, path: str, content: str) -> None: ...

    @abstractmethod
    async def delete_file(self, path: str) -> None: ...

    @abstractmethod
    async def search(self, query: str) -> list[VaultFile]: ...

    @abstractmethod
    async def get_backlinks(self, path: str) -> list[str]: ...

    @abstractmethod
    async def get_graph(self) -> dict[str, list[dict[str, str]]]: ...
