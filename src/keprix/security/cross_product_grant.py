"""CrossProductGrant: explicit grants allowing product B to read resources from product A."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CrossProductGrant:
    """A record that allows grantee_product_id to read one resource from grantor."""
    grant_id: str
    grantor_product_id: str
    grantee_product_id: str
    resource_kind: str        # "document" | "memory" | "skill"
    resource_id: str
    workspace_id: str
    granted_by: str           # user_id
    granted_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    scopes: list[str] = field(default_factory=lambda: ["read"])

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def is_write(self) -> bool:
        return "write" in self.scopes

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "grantor": self.grantor_product_id,
            "grantee": self.grantee_product_id,
            "resource": f"{self.resource_kind}/{self.resource_id}",
            "workspace_id": self.workspace_id,
            "scopes": self.scopes,
            "expires_at": self.expires_at,
            "is_expired": self.is_expired,
        }


class CrossProductGrantStore:
    """In-memory store for cross-product grants.

    Production implementations should persist grants to the database.

    Usage::

        store = CrossProductGrantStore()
        grant = CrossProductGrant(
            grant_id="g1",
            grantor_product_id="aiva",
            grantee_product_id="abbis",
            resource_kind="document",
            resource_id="doc-123",
            workspace_id="ws-abc",
            granted_by="user-1",
        )
        await store.add(grant)
        ok = await store.is_allowed("abbis", "document", "doc-123", "ws-abc", "read")
    """

    def __init__(self) -> None:
        self._grants: dict[str, CrossProductGrant] = {}
        self._lock = asyncio.Lock()

    async def add(self, grant: CrossProductGrant) -> None:
        async with self._lock:
            self._grants[grant.grant_id] = grant

    async def revoke(self, grant_id: str) -> None:
        async with self._lock:
            self._grants.pop(grant_id, None)

    async def is_allowed(
        self,
        grantee_product_id: str,
        resource_kind: str,
        resource_id: str,
        workspace_id: str,
        scope: str = "read",
    ) -> bool:
        async with self._lock:
            for grant in self._grants.values():
                if (
                    grant.grantee_product_id == grantee_product_id
                    and grant.resource_kind == resource_kind
                    and grant.resource_id == resource_id
                    and grant.workspace_id == workspace_id
                    and scope in grant.scopes
                    and not grant.is_expired
                ):
                    return True
        return False

    async def grants_for(self, grantee_product_id: str) -> list[CrossProductGrant]:
        async with self._lock:
            return [
                g for g in self._grants.values()
                if g.grantee_product_id == grantee_product_id and not g.is_expired
            ]

    async def purge_expired(self) -> int:
        async with self._lock:
            expired = [gid for gid, g in self._grants.items() if g.is_expired]
            for gid in expired:
                del self._grants[gid]
        return len(expired)
