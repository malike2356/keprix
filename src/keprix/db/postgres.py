"""PostgreSQL pool access for health monitoring."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from keprix.database import get_session_factory


async def get_pool() -> async_sessionmaker[AsyncSession]:
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("postgres session factory is not configured")
    return factory


async def ping() -> None:
    factory = await get_pool()
    async with factory() as session:
        await session.execute(text("SELECT 1"))
