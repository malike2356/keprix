# Hot backup

Create a tar.gz archive with `MANIFEST.json` and per-file sha256 checksums:

```bash
python3 scripts/keprix-backup snapshot
python3 scripts/keprix-backup verify backups/keprix_*.tar.gz
```

The admin UI also creates hot backups via `POST /api/admin/backup/create`.

CLI zip backup of `~/.keprix`:

```bash
python3 -m keprix.keprix_cli.main backup
```
