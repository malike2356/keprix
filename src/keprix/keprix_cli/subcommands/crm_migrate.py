"""``keprix crm-migrate`` thin CLI (Prompt 622)."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_crm_migrate_parser(
    subparsers: _SubParsersAction,
    *,
    cmd_crm_migrate: Callable,
) -> None:
    parser = subparsers.add_parser(
        "crm-migrate",
        help="Migrate CRM/outreach SQLite into Postgres (dry-run or apply)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        dest="crm_migrate_dry_run",
        action="store_true",
        help="Report per-table counts and checksums without writing",
    )
    mode.add_argument(
        "--apply",
        dest="crm_migrate_apply",
        action="store_true",
        help="Backup sqlite trees, upsert into Postgres, reconcile counts",
    )
    parser.add_argument("--crm-sqlite", dest="crm_sqlite", default=None)
    parser.add_argument("--outreach-sqlite", dest="outreach_sqlite", default=None)
    parser.add_argument(
        "--no-backup",
        dest="crm_migrate_no_backup",
        action="store_true",
        help="Skip zip backup (tests only)",
    )
    parser.set_defaults(func=cmd_crm_migrate)
