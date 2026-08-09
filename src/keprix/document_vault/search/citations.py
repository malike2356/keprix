"""Citation helpers for vault content retrieval (Prompt 652)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class VaultCitation:
    item_id: str
    revision: int
    name: str
    snippet: str
    score: float = 0.0
    source_id: str = ""
    workspace_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_source_id(workspace_id: str, item_id: str, revision: int) -> str:
    return f"{workspace_id}/{item_id}@r{int(revision)}"


__all__ = ["VaultCitation", "make_source_id"]
