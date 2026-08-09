"""Re-export CRM durable backend selector for outreach callers."""

from keprix.crm.durable import (
    force_postgres,
    postgres_engine_configured,
    postgres_sync_connectable,
    resolve_crm_backend,
    under_pytest,
)

__all__ = [
    "force_postgres",
    "postgres_engine_configured",
    "postgres_sync_connectable",
    "resolve_crm_backend",
    "under_pytest",
]
