"""SQLAlchemy async engine and session factory.

All models import Base from here so Alembic finds them via autogenerate.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from keprix.config.settings import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.KEPRIX_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.KEPRIX_LOG_LEVEL == "debug",
    )


engine: AsyncEngine = _make_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db(eng: AsyncEngine) -> None:
    """Create all tables that have not been created yet. Runs on startup."""
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
