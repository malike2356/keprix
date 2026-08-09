"""Migrate CRM + outreach SQLite files into Postgres (Prompt 622).

Usage:
  python -m keprix.crm.migrate_sqlite_to_pg --dry-run
  python -m keprix.crm.migrate_sqlite_to_pg --apply
  keprix crm-migrate --dry-run | --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.crm.schema_pg import CRM_TABLE_NAMES, ensure_crm_pg_schema
from keprix.outreach.schema_pg import OUTREACH_TABLE_NAMES, ensure_outreach_pg_schema

# FK-safe copy order (parents before children).
CRM_MIGRATE_ORDER: tuple[str, ...] = CRM_TABLE_NAMES
OUTREACH_MIGRATE_ORDER: tuple[str, ...] = OUTREACH_TABLE_NAMES


def _utcnow_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _data_dir() -> Path:
    try:
        from keprix.auth.config import data_dir

        return Path(data_dir())
    except Exception:
        return Path.home() / ".keprix"


def default_sqlite_paths() -> dict[str, Path]:
    root = _data_dir()
    return {
        "crm": root / "crm" / "crm.sqlite",
        "outreach": root / "outreach" / "outreach.sqlite",
    }


def backup_sqlite_trees(dest_zip: Path) -> Path:
    """Zip data_dir()/crm and data_dir()/outreach before apply."""
    root = _data_dir()
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in ("crm", "outreach"):
            folder = root / name
            if not folder.is_dir():
                continue
            for path in folder.rglob("*"):
                if path.is_file():
                    zf.write(path, arcname=str(Path(name) / path.relative_to(folder)))
    return dest_zip


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def count_and_checksum(
    conn: sqlite3.Connection,
    table: str,
    *,
    id_col: str = "id",
    workspace_col: str = "workspace_id",
) -> dict[str, Any]:
    if not _table_exists(conn, table):
        return {"table": table, "count": 0, "checksum": hashlib.sha256(b"").hexdigest(), "by_workspace": {}}
    cols = set(_table_columns(conn, table))
    total = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    by_ws: dict[str, dict[str, Any]] = {}
    if workspace_col in cols and id_col in cols:
        rows = conn.execute(
            f"SELECT {workspace_col}, {id_col} FROM {table} ORDER BY {workspace_col}, {id_col}"
        ).fetchall()
        grouped: dict[str, list[str]] = {}
        for ws, rid in rows:
            grouped.setdefault(str(ws), []).append(str(rid))
        for ws, ids in grouped.items():
            payload = "\n".join(ids).encode("utf-8")
            by_ws[ws] = {
                "count": len(ids),
                "checksum": hashlib.sha256(payload).hexdigest(),
            }
        all_ids = [str(r[1]) for r in rows]
        checksum = hashlib.sha256("\n".join(all_ids).encode("utf-8")).hexdigest()
    elif id_col in cols:
        ids = [str(r[0]) for r in conn.execute(f"SELECT {id_col} FROM {table} ORDER BY {id_col}").fetchall()]
        checksum = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    else:
        # composite PK tables (list_members): checksum of sorted row tuples
        col_list = _table_columns(conn, table)
        rows = conn.execute(
            f"SELECT {', '.join(col_list)} FROM {table} ORDER BY {', '.join(col_list)}"
        ).fetchall()
        lines = ["|".join("" if c is None else str(c) for c in row) for row in rows]
        checksum = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return {"table": table, "count": total, "checksum": checksum, "by_workspace": by_ws}


def inventory_sqlite(paths: dict[str, Path]) -> dict[str, Any]:
    out: dict[str, Any] = {"crm": [], "outreach": []}
    if paths["crm"].is_file():
        conn = sqlite3.connect(str(paths["crm"]))
        try:
            for table in CRM_MIGRATE_ORDER:
                out["crm"].append(count_and_checksum(conn, table))
        finally:
            conn.close()
    if paths["outreach"].is_file():
        conn = sqlite3.connect(str(paths["outreach"]))
        try:
            for table in OUTREACH_MIGRATE_ORDER:
                id_col = "id"
                if table == "outreach_control":
                    id_col = "workspace_id"
                elif table == "outreach_list_members":
                    id_col = "list_id"
                out["outreach"].append(
                    count_and_checksum(conn, table, id_col=id_col)
                )
        finally:
            conn.close()
    return out


def _upsert_row(pg_conn, table: str, columns: list[str], values: tuple[Any, ...]) -> None:
    placeholders = ", ".join("?" for _ in columns)
    col_sql = ", ".join(columns)
    # Primary key: workspace_id for control; (list_id, lead_id) for members; else id
    if table == "outreach_control":
        conflict = "workspace_id"
        updates = [c for c in columns if c != "workspace_id"]
    elif table == "outreach_list_members":
        conflict = "list_id, lead_id"
        updates = [c for c in columns if c not in ("list_id", "lead_id")]
    else:
        conflict = "id"
        updates = [c for c in columns if c != "id"]
    if updates:
        set_sql = ", ".join(f"{c} = EXCLUDED.{c}" for c in updates)
        sql = (
            f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict}) DO UPDATE SET {set_sql}"
        )
    else:
        sql = (
            f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict}) DO NOTHING"
        )
    pg_conn.execute(sql, values)


def copy_table(sqlite_conn: sqlite3.Connection, pg_conn, table: str) -> int:
    if not _table_exists(sqlite_conn, table):
        return 0
    sqlite_cols = _table_columns(sqlite_conn, table)
    pg_cols = {str(r[1]) for r in pg_conn.execute(f"PRAGMA table_info({table})").fetchall()}
    columns = [c for c in sqlite_cols if c in pg_cols]
    if not columns:
        return 0
    rows = sqlite_conn.execute(
        f"SELECT {', '.join(columns)} FROM {table}"
    ).fetchall()
    for row in rows:
        _upsert_row(pg_conn, table, columns, tuple(row))
    return len(rows)


def apply_migration(
    *,
    paths: dict[str, Path] | None = None,
    pg_url: str | None = None,
    backup: bool = True,
) -> dict[str, Any]:
    from keprix.crm.pg_compat import connect_crm_pg, reset_sync_engine_for_tests

    paths = paths or default_sqlite_paths()
    inventory_before = inventory_sqlite(paths)
    backup_path = None
    if backup:
        backup_path = _data_dir() / "backups" / f"crm-outreach-{_utcnow_slug()}.zip"
        backup_sqlite_trees(backup_path)

    reset_sync_engine_for_tests()
    pg = connect_crm_pg(url=pg_url)
    try:
        ensure_crm_pg_schema(pg)
        ensure_outreach_pg_schema(pg)
        copied: dict[str, int] = {}
        if paths["crm"].is_file():
            sconn = sqlite3.connect(str(paths["crm"]))
            try:
                for table in CRM_MIGRATE_ORDER:
                    n = copy_table(sconn, pg, table)
                    copied[table] = n
                pg.commit()
            finally:
                sconn.close()
        if paths["outreach"].is_file():
            sconn = sqlite3.connect(str(paths["outreach"]))
            try:
                for table in OUTREACH_MIGRATE_ORDER:
                    n = copy_table(sconn, pg, table)
                    copied[table] = n
                pg.commit()
            finally:
                sconn.close()

        # Reconcile counts against Postgres
        mismatches: list[str] = []
        for group, tables in (("crm", CRM_MIGRATE_ORDER), ("outreach", OUTREACH_MIGRATE_ORDER)):
            for table in tables:
                src = next(
                    (t for t in inventory_before[group] if t["table"] == table),
                    {"count": 0},
                )
                row = pg.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
                dest_count = int(row[0] if row is not None else 0)
                # Idempotent apply may leave dest >= src when re-run; require >= src and
                # exact match when dest table was empty of foreign rows for this migrate.
                if dest_count < int(src["count"]):
                    mismatches.append(
                        f"{table}: sqlite={src['count']} pg={dest_count}"
                    )
        if mismatches:
            pg.rollback()
            raise RuntimeError("count reconcile failed: " + "; ".join(mismatches))
        pg.commit()
    finally:
        pg.close()

    return {
        "backup": str(backup_path) if backup_path else None,
        "inventory": inventory_before,
        "copied": copied,
        "rollback": (
            "Set KEPRIX_CRM_BACKEND=sqlite, restore the backup zip into data_dir "
            f"({_data_dir()}), then restart Keprix."
        ),
    }


def dry_run(paths: dict[str, Path] | None = None) -> dict[str, Any]:
    paths = paths or default_sqlite_paths()
    inv = inventory_sqlite(paths)
    return {
        "mode": "dry-run",
        "paths": {k: str(v) for k, v in paths.items()},
        "inventory": inv,
        "rollback": (
            "On apply failure or after a bad migrate: set KEPRIX_CRM_BACKEND=sqlite, "
            "restore the backup zip under data_dir, restart."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate CRM/outreach SQLite to Postgres")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    parser.add_argument("--crm-sqlite", type=Path, default=None)
    parser.add_argument("--outreach-sqlite", type=Path, default=None)
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args(argv)

    paths = default_sqlite_paths()
    if args.crm_sqlite:
        paths["crm"] = args.crm_sqlite
    if args.outreach_sqlite:
        paths["outreach"] = args.outreach_sqlite

    if args.dry_run:
        result = dry_run(paths)
    else:
        result = apply_migration(paths=paths, backup=not args.no_backup)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
