"""Outreach automation schema SQL (Postgres TEXT ids; Prompt 622).

Kept in sync with ``outreach/schema_pg.py`` and SQLite store/ops.
The prior UUID Alembic 024 schema is superseded by migration 028.
"""

from keprix.outreach.schema_pg import OUTREACH_PG_SCHEMA_SQL as OUTREACH_SCHEMA_SQL

__all__ = ["OUTREACH_SCHEMA_SQL"]
