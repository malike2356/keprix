"""IsolationQueryFilter: enforce namespace isolation on data access."""

from __future__ import annotations

import logging
from typing import Any

from .isolation_violation import IsolationViolation
from .product_context import get_product_context, get_product_context_or_none

logger = logging.getLogger(__name__)

ISOLATED_TABLES: frozenset[str] = frozenset({
    "memories",
    "skills",
    "tasks",
    "sessions",
    "session_messages",
    "documents",
    "retrieval_graph_edges",
    "playbook_runs",
    "tool_audit_log",
    "brain_share_links",
})


class IsolatedDataPlane:
    """Wrapper that validates raw SQL queries enforce namespace isolation.

    Usage::

        plane = IsolatedDataPlane(underlying_data_plane)
        rows = plane.execute(
            "SELECT * FROM memories WHERE workspace_id = :workspace_id",
            [workspace_id],
        )
    """

    def __init__(self, plane: Any) -> None:
        self._plane = plane

    def execute(self, sql: str, params: list | None = None) -> Any:
        """Execute SQL, raising IsolationViolation if isolation rules are broken."""
        params = params or []
        ctx = get_product_context_or_none()

        if ctx is None:
            # No context means we're in a non-request context (startup, migration).
            return self._plane.execute(sql, params)

        # Detect queries on isolated tables
        sql_upper = sql.upper()
        for table in ISOLATED_TABLES:
            if table.upper() in sql_upper:
                # Require a WHERE clause
                if "WHERE" not in sql_upper:
                    raise IsolationViolation(
                        f"Raw query on isolated table {table!r} without WHERE clause: "
                        f"{sql[:100]}",
                        product_id=ctx.product_id,
                        workspace_id=ctx.workspace_id,
                        table=table,
                    )
                break

        return self._plane.execute(sql, params)

    def execute_isolated(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Execute SQL with workspace_id + product_id automatically injected.

        The SQL MUST contain :workspace_id placeholder; :product_id is optional.
        """
        ctx = get_product_context()
        params = dict(params or {})
        params.setdefault("workspace_id", ctx.workspace_id)
        params.setdefault("product_id", ctx.product_id)
        return self._plane.execute(sql, params)


def check_isolation(table: str, workspace_id: str, product_id: str) -> None:
    """Assert that the current context matches the given workspace and product.

    Call this in repositories as an explicit guard before returning data.
    """
    ctx = get_product_context_or_none()
    if ctx is None:
        return  # no context = no enforcement (e.g., background jobs)

    if workspace_id and ctx.workspace_id and workspace_id != ctx.workspace_id:
        raise IsolationViolation(
            f"Workspace mismatch on table {table!r}: "
            f"context={ctx.workspace_id!r} data={workspace_id!r}",
            product_id=ctx.product_id,
            workspace_id=ctx.workspace_id,
            table=table,
        )

    if product_id and ctx.product_id and not ctx.is_base_product():
        if product_id != ctx.product_id:
            raise IsolationViolation(
                f"Product mismatch on table {table!r}: "
                f"context={ctx.product_id!r} data={product_id!r}",
                product_id=ctx.product_id,
                workspace_id=ctx.workspace_id,
                table=table,
            )
