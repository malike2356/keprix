"""Token metering for agent runs (Prompt 57)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenEntry:
    run_id: str
    workspace_id: str
    tokens: dict[str, int] = field(default_factory=dict)


class TokenMeter:
    def __init__(self) -> None:
        self._entries: list[TokenEntry] = []

    def record(
        self,
        run_id: str,
        tokens: dict[str, int],
        *,
        workspace_id: str = "",
    ) -> None:
        self._entries.append(TokenEntry(run_id=run_id, workspace_id=workspace_id, tokens=dict(tokens)))

    def totals(self, *, workspace_id: str | None = None) -> dict[str, int]:
        entries = self._entries
        if workspace_id:
            entries = [entry for entry in entries if entry.workspace_id == workspace_id]
        totals: dict[str, int] = {}
        for entry in entries:
            for key, value in entry.tokens.items():
                totals[key] = totals.get(key, 0) + int(value)
        return totals

    def dashboard(self, *, limit: int = 20) -> dict[str, Any]:
        return {
            "totals": self.totals(),
            "run_count": len(self._entries),
            "recent": [
                {"run_id": entry.run_id, "workspace_id": entry.workspace_id, "tokens": entry.tokens}
                for entry in self._entries[-limit:]
            ],
        }

    def clear(self) -> None:
        self._entries.clear()


_token_meter: TokenMeter | None = None


def get_token_meter() -> TokenMeter:
    global _token_meter
    if _token_meter is None:
        _token_meter = TokenMeter()
    return _token_meter


def record_tokens(run_id: str, tokens: dict[str, int], *, workspace_id: str = "") -> None:
    get_token_meter().record(run_id, tokens, workspace_id=workspace_id)
