"""Tenant and membership records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

TenantStatus = Literal["active", "suspended", "deleted"]
MembershipRole = Literal["owner", "admin", "member", "viewer"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Tenant:
    id: str
    slug: str
    display_name: str
    owner_user_id: str
    status: TenantStatus = "active"
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: _utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "Tenant":
        return cls(
            id=str(row["id"]),
            slug=str(row["slug"]).strip().lower(),
            display_name=str(row.get("display_name") or row.get("name") or row["slug"]),
            owner_user_id=str(row.get("owner_user_id") or ""),
            status=str(row.get("status") or "active"),  # type: ignore[arg-type]
            created_at=str(row.get("created_at") or _utcnow().isoformat()),
            updated_at=str(row.get("updated_at") or _utcnow().isoformat()),
            metadata=dict(row.get("metadata") or {}),
        )


@dataclass
class Membership:
    tenant_id: str
    user_id: str
    role: MembershipRole = "member"
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "Membership":
        return cls(
            tenant_id=str(row["tenant_id"]),
            user_id=str(row["user_id"]),
            role=str(row.get("role") or "member"),  # type: ignore[arg-type]
            created_at=str(row.get("created_at") or _utcnow().isoformat()),
        )
