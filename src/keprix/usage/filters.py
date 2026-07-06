"""Query filters for LLM usage analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class UsageQueryFilters:
    workspace_id: str = "default"
    user_id: str | None = None
    channel: str | None = None
    model: str | None = None
    provider: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    days: int | None = 30

    def window(self) -> tuple[datetime, datetime]:
        until = self.until or datetime.now(timezone.utc)
        if self.since is not None:
            since = self.since
            if since.tzinfo is None:
                since = since.replace(tzinfo=timezone.utc)
            return since, until
        days = max(1, int(self.days or 30))
        return until - timedelta(days=days), until

    @classmethod
    def from_params(
        cls,
        *,
        workspace_id: str = "default",
        user_id: str | None = None,
        channel: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        days: int | None = 30,
        from_ts: datetime | None = None,
        to_ts: datetime | None = None,
    ) -> UsageQueryFilters:
        return cls(
            workspace_id=workspace_id,
            user_id=user_id,
            channel=channel,
            model=model,
            provider=provider,
            days=days,
            since=from_ts,
            until=to_ts,
        )
