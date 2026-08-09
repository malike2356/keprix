"""CRM/outreach durable backend selection (Prompt 622).

Env:
  KEPRIX_CRM_BACKEND = auto | sqlite | postgres (default auto)
  KEPRIX_CRM_DB_PATH = optional SQLite file override
  KEPRIX_DATABASE_URL = shared Postgres URL (async driver OK)
  KEPRIX_CRM_FORCE_PG = 1 forces Postgres under pytest / auto
"""

from __future__ import annotations

import os
import sys
from typing import Literal

CrmBackend = Literal["sqlite", "postgres"]


def under_pytest() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules


def force_postgres() -> bool:
    return os.environ.get("KEPRIX_CRM_FORCE_PG", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def postgres_engine_configured() -> bool:
    """True when the shared async engine/session factory can be created."""
    try:
        from keprix.database import get_engine, get_session_factory

        engine = get_engine()
        if engine is None:
            return False
        return get_session_factory() is not None
    except Exception:
        return False


def postgres_sync_connectable() -> bool:
    """True when a sync psycopg connection succeeds (best-effort ping)."""
    try:
        from keprix.crm.pg_compat import ping_postgres

        return ping_postgres()
    except Exception:
        return False


def resolve_crm_backend() -> CrmBackend:
    """Select sqlite or postgres for CRM and outreach stores."""
    raw = (os.environ.get("KEPRIX_CRM_BACKEND") or "auto").strip().lower()
    if raw in ("sqlite", "postgres"):
        return raw  # type: ignore[return-value]

    # auto
    prefer_pg = force_postgres() or not under_pytest()
    if not prefer_pg:
        return "sqlite"
    if not postgres_engine_configured():
        return "sqlite"
    if not postgres_sync_connectable():
        return "sqlite"
    return "postgres"


def sqlite_crm_path_from_env() -> str | None:
    raw = (os.environ.get("KEPRIX_CRM_DB_PATH") or "").strip()
    return raw or None
