"""CRM lead ingest CLI handlers (Prompt 621)."""

from __future__ import annotations

from keprix.crm.ingestion.__main__ import main as ingestion_main


def cmd_crm_ingest(args) -> int:
    """Delegate to python -m keprix.crm.ingestion argument shape."""
    command = getattr(args, "crm_ingest_command", None)
    if not command:
        return 2
    argv = [command]
    path = getattr(args, "path", None)
    if path:
        argv.append(path)
    if getattr(args, "workspace_id", None):
        argv.extend(["--workspace-id", str(args.workspace_id)])
    if command == "preview" and getattr(args, "limit", None) is not None:
        argv.extend(["--limit", str(args.limit)])
    if command == "import":
        if getattr(args, "overwrite", False):
            argv.append("--overwrite")
        if getattr(args, "dry_run", False):
            argv.append("--dry-run")
        if getattr(args, "source_name", None):
            argv.extend(["--source-name", str(args.source_name)])
    if command == "export" and getattr(args, "format", None):
        argv.extend(["--format", str(args.format)])
    return ingestion_main(argv)
