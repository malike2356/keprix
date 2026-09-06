"""Tenant-aware SQLAlchemy sessions for PostgreSQL RLS."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from keprix.security.product_context import get_product_context_or_none


class TenantAsyncSession(AsyncSession):
    """Set the RLS tenant inside each transaction, never on the pool."""

    _tenant_setting_set = False

    async def _set_tenant_setting(self) -> None:
        if self._tenant_setting_set:
            return
        try:
            bind = self.sync_session.get_bind()
            if bind.dialect.name != "postgresql":
                return
        except Exception:
            return
        context = get_product_context_or_none()
        tenant_id = str(context.tenant_id).strip() if context and context.tenant_id else ""
        if not tenant_id:
            return
        await super().execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )
        self._tenant_setting_set = True

    async def execute(self, statement: Any, params: Any = None, **kwargs: Any):
        await self._set_tenant_setting()
        return await super().execute(statement, params, **kwargs)

    async def commit(self) -> None:
        try:
            await super().commit()
        finally:
            self._tenant_setting_set = False

    async def rollback(self) -> None:
        try:
            await super().rollback()
        finally:
            self._tenant_setting_set = False

    async def close(self) -> None:
        try:
            await super().close()
        finally:
            self._tenant_setting_set = False
