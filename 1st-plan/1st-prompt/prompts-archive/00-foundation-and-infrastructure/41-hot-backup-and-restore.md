# keprix - Prompt 41: Hot Backup and Restore

## Context

Reference: `planning/agents-to-adopt/odysseus/docs/backup-restore.md`.

keprix stores all of its state in a data directory: the SQLite database (or Postgres), the vault key, memory, RAG indexes, workspace documents, and uploads. Prompt 08 (vault) and Prompt 10 (documents) define where this data lives. What no existing prompt defines is how an operator safely backs it up and restores it.

The critical constraint: backups must be safe to take while keprix is running. Raw file copy of a SQLite database while writes are in flight produces a corrupt snapshot. The solution is SQLite's own `.backup()` API, which streams an internally consistent snapshot from a live database without blocking reads or writes. This is the only correct approach.

The backup tool must also:
- Exclude large, re-derivable data by default (research outputs, cached attachments).
- Produce a verifiable archive (manifest + checksum, not just a tarball).
- Restore safely with an explicit confirmation step (restore is destructive).
- Work without the app's virtualenv active (standard library only for the script itself).

This prompt builds `keprix backup`: a CLI command and a script that handles snapshot, list, verify, and restore operations.

---

## File Structure

```
keprix/scripts/
    keprix-backup              - executable Python script (stdlib only)

keprix/backend/admin/
    backup.py                  - BackupManager: Python API used by CLI and API endpoint
    routes_backup.py           - admin API endpoints

keprix/tests/admin/
    test_backup.py

keprix/ui/web/src/app/(workspace)/settings/admin/
    backup/page.tsx            - backup management UI (admin only)
```

---

## Data Directory Layout

The data directory is the single source of truth for all keprix state:

```
data/
    app.db                 - SQLite database (main store)
    .app_key               - Fernet encryption key for the vault
    vault/                 - encrypted credential files
    memory/                - episodic memory store (embeddings + text)
    rag/                   - RAG indexes (vector store files)
    documents/             - workspace documents and uploads
    uploads/               - user-uploaded files
    research/              - deep research outputs (EXCLUDED by default: large, re-derivable)
    mail-attachments/      - cached IMAP extractions (EXCLUDED by default: re-derivable)
    sessions/              - active session state (EXCLUDED by default: ephemeral)
```

Default excludes: `research/`, `mail-attachments/`, `sessions/`. These can be included with flags.

---

## Backup Script

```python
#!/usr/bin/env python3
# keprix/scripts/keprix-backup
#
# Standard library only. No dependency on the app virtualenv.
# Usage:
#   keprix-backup snapshot [--out PATH] [--include-research] [--include-attachments]
#   keprix-backup list [--backup-dir PATH]
#   keprix-backup verify ARCHIVE
#   keprix-backup restore ARCHIVE --yes [--data-dir PATH]

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR_DEFAULT = Path("data")
BACKUP_DIR_DEFAULT = Path("backups")

ALWAYS_EXCLUDE = {"sessions"}
DEFAULT_EXCLUDE = {"research", "mail-attachments"}
SENSITIVE_NOTE = (
    "WARNING: This backup contains your vault encryption key (.app_key) and "
    "all stored credentials. Store it securely. Never commit to git."
)


def snapshot(args):
    data_dir = Path(args.data_dir) if hasattr(args, "data_dir") and args.data_dir else DATA_DIR_DEFAULT
    backup_dir = Path(args.backup_dir) if hasattr(args, "backup_dir") and args.backup_dir else BACKUP_DIR_DEFAULT

    if not data_dir.exists():
        _fail(f"Data directory not found: {data_dir}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_path = Path(args.out) if args.out else backup_dir / f"keprix-backup-{ts}.tar.gz"

    if out_path.resolve().is_relative_to(data_dir.resolve()):
        _fail("Output path must be outside the data directory.")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    excludes = set(ALWAYS_EXCLUDE)
    if not getattr(args, "include_research", False):
        excludes.add("research")
    if not getattr(args, "include_attachments", False):
        excludes.add("mail-attachments")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        stage = tmp_path / "stage"
        stage.mkdir()

        manifest_entries = []

        # SQLite backup via backup API (safe while app is running)
        db_path = data_dir / "app.db"
        if db_path.exists():
            staged_db = stage / "app.db"
            _sqlite_backup(db_path, staged_db)
            manifest_entries.append(_manifest_entry(staged_db, "app.db"))

        # Copy all other files/directories except excludes
        for item in sorted(data_dir.iterdir()):
            if item.name == "app.db":
                continue
            if item.name in excludes:
                continue
            dest = stage / item.name
            if item.is_dir():
                shutil.copytree(item, dest, symlinks=False)
            else:
                shutil.copy2(item, dest)
            for f in (dest.rglob("*") if dest.is_dir() else [dest]):
                if f.is_file():
                    manifest_entries.append(_manifest_entry(f, str(f.relative_to(stage))))

        # Write manifest
        manifest = {
            "keprix_backup_version": "1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data_dir": str(data_dir.resolve()),
            "excluded": sorted(excludes),
            "note": SENSITIVE_NOTE,
            "files": manifest_entries,
        }
        (stage / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))

        # Create gzip tarball from stage
        with tarfile.open(out_path, "w:gz") as tar:
            tar.add(stage, arcname=".")

    result = {
        "path": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "file_count": len(manifest_entries),
        "excluded": sorted(excludes),
    }
    _print_result(result, args)


def _sqlite_backup(src: Path, dest: Path) -> None:
    """
    Uses sqlite3.Connection.backup() to copy a live SQLite database safely.
    This is the only correct way to snapshot SQLite while writes may be in flight.
    """
    src_conn = sqlite3.connect(str(src))
    dest_conn = sqlite3.connect(str(dest))
    try:
        src_conn.backup(dest_conn)
    finally:
        dest_conn.close()
        src_conn.close()


def _manifest_entry(path: Path, name: str) -> dict:
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"name": name, "sha256": sha256, "size_bytes": path.stat().st_size}


def verify(args):
    archive = Path(args.archive)
    if not archive.exists():
        _fail(f"Archive not found: {archive}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(archive, "r:gz") as tar:
            # Safety: reject any entries with absolute paths or path traversal
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    _fail(f"Archive contains unsafe path: {member.name}")
            tar.extractall(tmp_path)

        manifest_path = tmp_path / "MANIFEST.json"
        if not manifest_path.exists():
            _fail("Archive does not contain MANIFEST.json. It may be corrupt or not a keprix backup.")

        manifest = json.loads(manifest_path.read_text())
        errors = []
        for entry in manifest.get("files", []):
            file_path = tmp_path / entry["name"]
            if not file_path.exists():
                errors.append(f"MISSING: {entry['name']}")
                continue
            actual_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if actual_sha != entry["sha256"]:
                errors.append(f"CHECKSUM MISMATCH: {entry['name']}")

        result = {
            "archive": str(archive),
            "created_at": manifest.get("created_at"),
            "file_count": len(manifest.get("files", [])),
            "errors": errors,
            "valid": len(errors) == 0,
        }
        _print_result(result, args)


def restore(args):
    archive = Path(args.archive)
    if not archive.exists():
        _fail(f"Archive not found: {archive}")

    if not getattr(args, "yes", False):
        _fail("Restore is destructive. Pass --yes to confirm.")

    data_dir = Path(args.data_dir) if hasattr(args, "data_dir") and args.data_dir else DATA_DIR_DEFAULT

    # Verify integrity first
    verify(args)  # will exit on error

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    _fail(f"Archive contains unsafe path: {member.name}")
            tar.extractall(tmp_path)

        # Rename existing data dir to data.bak.<timestamp>
        if data_dir.exists():
            bak = data_dir.parent / f"{data_dir.name}.bak.{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            data_dir.rename(bak)
            print(f"Previous data directory moved to: {bak}", file=sys.stderr)

        # Copy extracted content (exclude MANIFEST.json) to data dir
        data_dir.mkdir(parents=True)
        for item in tmp_path.iterdir():
            if item.name == "MANIFEST.json":
                continue
            dest = data_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    print(json.dumps({"restored": True, "data_dir": str(data_dir)}, indent=2))


def list_backups(args):
    backup_dir = Path(args.backup_dir) if hasattr(args, "backup_dir") and args.backup_dir else BACKUP_DIR_DEFAULT
    if not backup_dir.exists():
        _print_result({"backups": []}, args)
        return

    backups = []
    for f in sorted(backup_dir.glob("keprix-backup-*.tar.gz"), reverse=True):
        backups.append({
            "path": str(f),
            "size_bytes": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
        })

    _print_result({"backups": backups}, args)


def _fail(msg: str):
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


def _print_result(result: dict, args):
    if getattr(args, "pretty", False):
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
```

---

## BackupManager Python API

For use by the admin API endpoint and scheduled cron jobs:

```python
# keprix/backend/admin/backup.py

class BackupManager:
    """Python API wrapping the backup script logic for use by the API and cron."""

    def __init__(self, data_dir: Path, backup_dir: Path):
        self.data_dir = data_dir
        self.backup_dir = backup_dir

    async def create_snapshot(
        self,
        include_research: bool = False,
        include_attachments: bool = False,
        out_path: Path | None = None,
    ) -> dict:
        """Creates a backup snapshot. Returns the result dict."""
        # Runs the script logic directly (not via subprocess to avoid venv dependency issues).
        ...

    async def list_snapshots(self) -> list[dict]:
        """Lists available backups in the backup directory."""
        ...

    async def verify_snapshot(self, archive_path: Path) -> dict:
        """Verifies a backup archive without extracting to data dir."""
        ...

    async def schedule_daily(self, hour: int = 3) -> None:
        """Registers a daily backup cron job (Prompt 15). Runs at the specified hour UTC."""
        await cron_scheduler.register(
            name="daily_backup",
            schedule=f"0 {hour} * * *",
            handler=self.create_snapshot,
        )
```

---

## API Endpoints (Admin Only)

```
POST   /api/admin/backup/snapshot
       Body: { include_research?: bool, include_attachments?: bool }
       Admin only. Creates a snapshot immediately.
       Returns: { path, size_bytes, file_count, excluded }

GET    /api/admin/backup/snapshots
       Returns: list of snapshots in the backup directory

GET    /api/admin/backup/snapshots/{filename}/verify
       Returns: verification result for the named snapshot

POST   /api/admin/backup/restore
       Body: { filename, confirm: true }
       Admin only. Requires `confirm: true` in the body (not just a flag).
       Stops the app, restores, restarts.
       Returns: { restored: true } or error.
       NOTE: This endpoint is dangerous. It must check that `confirm === true`
       as a body field, not just a query param, to prevent accidental invocation.

GET    /api/admin/backup/schedule
       Returns: current backup schedule config

PUT    /api/admin/backup/schedule
       Body: { enabled: bool, hour_utc: 0-23, retain_days: int }
       Sets the automatic backup schedule.
```

---

## Admin UI

`/settings/admin/backup`

**Current backup status:** Last backup date and size. "Create backup now" button.

**Backup schedule:** Toggle (enabled/disabled). Hour-of-day selector (UTC). Retention period (number of days to keep old backups). Save button.

**Backup list:** Table of existing backups with filename, date, size, verify button, and restore button. Restore button shows a confirmation dialog: "This will replace your current data directory. This cannot be undone. Type RESTORE to confirm."

**Security note:** A yellow banner at the top of the page: "Backup files contain your vault encryption key and all credentials. Store them securely. Do not expose them via HTTP or commit them to git."

---

## Cron Cleanup

```python
# In cron scheduler (Prompt 15):
# Runs daily after the backup job. Deletes backups older than retain_days.

async def cleanup_old_backups(backup_dir: Path, retain_days: int = 30) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - (retain_days * 86400)
    for f in backup_dir.glob("keprix-backup-*.tar.gz"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
```

---

## Acceptance Criteria

- `_sqlite_backup(src, dest)` produces an internally consistent SQLite file even when writes are happening concurrently (verified by running a write loop in a thread during backup and then opening the dest with `sqlite3.connect`).
- `snapshot()` excludes `research/`, `mail-attachments/`, and `sessions/` by default.
- `snapshot()` fails with a clear error if `--out` is inside the data directory.
- `snapshot()` produces a `MANIFEST.json` with a `sha256` entry for every copied file.
- `verify()` returns `valid: true` for an untampered archive.
- `verify()` returns `valid: false` and lists the affected files if any file is tampered.
- `verify()` rejects archives containing path traversal (e.g. `../../etc/passwd`).
- `restore()` without `--yes` exits with a non-zero code and a clear error message.
- `restore()` with `--yes` renames the existing data directory to `data.bak.<timestamp>` before restoring.
- The script runs without the app virtualenv: `python3 keprix-backup snapshot` works with only stdlib.
- `POST /api/admin/backup/restore` without `confirm: true` in the body returns HTTP 422.
- The backup cron job runs at 03:00 UTC by default and is registered via the cron scheduler (Prompt 15).
- `cleanup_old_backups()` deletes archives older than `retain_days` and leaves newer ones untouched.
