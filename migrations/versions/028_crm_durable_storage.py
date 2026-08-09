"""Alembic: CRM durable storage + outreach TEXT-id schema (Prompt 622).

Creates crm_* tables (TEXT ids). Drops unused UUID outreach tables from 024
(when present) and recreates outreach_* with TEXT ids + workspace_id on every table.
"""

from __future__ import annotations

from alembic import op

revision = "028_crm_durable_storage"
down_revision = "027_aiva_analytics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from keprix.crm.schema_pg import CRM_PG_SCHEMA_SQL
    from keprix.outreach.schema_pg import (
        OUTREACH_DROP_UUID_TABLES_SQL,
        OUTREACH_PG_SCHEMA_SQL,
    )

    for stmt in _split(CRM_PG_SCHEMA_SQL):
        op.execute(stmt)

    for stmt in _split(OUTREACH_DROP_UUID_TABLES_SQL):
        op.execute(stmt)

    for stmt in _split(OUTREACH_PG_SCHEMA_SQL):
        op.execute(stmt)


def downgrade() -> None:
    # Do not drop CRM tables on downgrade (data loss). Outreach TEXT tables stay;
    # restoring UUID 024 shapes is intentional non-support after 622.
    pass


def _split(script: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    in_single = False
    for ch in script:
        if ch == "'":
            in_single = not in_single
            buf.append(ch)
            continue
        if ch == ";" and not in_single:
            stmt = "".join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts
