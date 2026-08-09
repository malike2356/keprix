"""Alembic: Document Vault canonical tables (Prompt 646)."""

from __future__ import annotations

from alembic import op

revision = "029_document_vault"
down_revision = "028_crm_durable_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from keprix.document_vault.schema import PG_SCHEMA

    for stmt in _split(PG_SCHEMA):
        op.execute(stmt)


def downgrade() -> None:
    # Do not drop vault tables on downgrade (data loss).
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
