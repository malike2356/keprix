"""``keprix crm-migrate`` CLI (Prompt 622)."""

from __future__ import annotations

from keprix.crm.migrate_sqlite_to_pg import main as migrate_main


def cmd_crm_migrate(args) -> int:
    argv: list[str] = []
    if getattr(args, "crm_migrate_dry_run", False):
        argv.append("--dry-run")
    if getattr(args, "crm_migrate_apply", False):
        argv.append("--apply")
    if getattr(args, "crm_migrate_no_backup", False):
        argv.append("--no-backup")
    if getattr(args, "crm_sqlite", None):
        argv.extend(["--crm-sqlite", str(args.crm_sqlite)])
    if getattr(args, "outreach_sqlite", None):
        argv.extend(["--outreach-sqlite", str(args.outreach_sqlite)])
    if not argv or ("--dry-run" not in argv and "--apply" not in argv):
        argv = ["--dry-run"]
    return migrate_main(argv)
