"""PostgreSQL persistence helpers for vault items."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from sqlalchemy import delete, select

from keprix.database import get_session_factory
from keprix.db.models import VaultItemRow
from keprix.security.vault_service import VaultItem


def _use_db() -> bool:
    if "pytest" in sys.modules:
        return False
    return get_session_factory() is not None


async def persist_vault_item(item: VaultItem, blob: bytes) -> None:
    if not _use_db():
        return
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        row = await session.get(VaultItemRow, item.id)
        if row is None:
            row = VaultItemRow(
                id=item.id,
                user_id=item.user_id,
                label=item.label,
                category=item.category,
                username=item.username,
                value_encrypted=blob,
                url=item.url,
                tags=item.tags,
            )
            session.add(row)
        else:
            row.label = item.label
            row.category = item.category
            row.username = item.username
            row.value_encrypted = blob
            row.url = item.url
            row.tags = item.tags
            row.updated_at = datetime.now(timezone.utc)
        await session.commit()


async def load_vault_item(item_id: str, user_id: str) -> tuple[VaultItem, bytes] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        row = await session.get(VaultItemRow, item_id)
        if row is None or row.user_id != user_id:
            return None
        item = VaultItem(
            id=row.id,
            user_id=row.user_id,
            label=row.label,
            category=row.category,
            username=row.username,
            url=row.url,
            tags=list(row.tags or []),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        return item, bytes(row.value_encrypted)


async def list_vault_items(
    user_id: str, *, category: str | None = None
) -> list[tuple[VaultItem, bytes]]:
    if not _use_db():
        return []
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        stmt = select(VaultItemRow).where(VaultItemRow.user_id == user_id)
        if category:
            stmt = stmt.where(VaultItemRow.category == category)
        rows = (await session.execute(stmt)).scalars().all()
        out: list[tuple[VaultItem, bytes]] = []
        for row in rows:
            item = VaultItem(
                id=row.id,
                user_id=row.user_id,
                label=row.label,
                category=row.category,
                username=row.username,
                url=row.url,
                tags=list(row.tags or []),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            out.append((item, bytes(row.value_encrypted)))
        return out


async def delete_vault_item(item_id: str, user_id: str) -> None:
    if not _use_db():
        return
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        await session.execute(
            delete(VaultItemRow).where(
                VaultItemRow.id == item_id, VaultItemRow.user_id == user_id
            )
        )
        await session.commit()
