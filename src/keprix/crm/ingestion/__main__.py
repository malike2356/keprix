"""Thin CLI: python -m keprix.crm.ingestion ..."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m keprix.crm.ingestion",
        description="Canonical CRM lead spreadsheet ingestion (Prompt 621)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    preview = sub.add_parser("preview", help="Preview header mapping for a file")
    preview.add_argument("path")
    preview.add_argument("--workspace-id", default="default")
    preview.add_argument("--limit", type=int, default=5)

    import_p = sub.add_parser("import", help="Import leads from a spreadsheet")
    import_p.add_argument("path")
    import_p.add_argument("--workspace-id", required=True)
    import_p.add_argument("--overwrite", action="store_true")
    import_p.add_argument("--source-name", default=None)
    import_p.add_argument("--dry-run", action="store_true")

    export_p = sub.add_parser("export", help="Export workspace leads (xlsx default)")
    export_p.add_argument("path")
    export_p.add_argument("--workspace-id", required=True)
    export_p.add_argument("--format", choices=["xlsx", "csv"], default="xlsx")

    args = parser.parse_args(argv)

    if args.command == "preview":
        from keprix.crm.ingestion.readers import read_path
        from keprix.crm.ingestion.service import preview_rows

        loaded = read_path(args.path)
        result = preview_rows(loaded["rows"], limit=args.limit)
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "import":
        from keprix.crm.ingestion.service import IngestOptions, ingest_file

        options = IngestOptions(
            overwrite=bool(args.overwrite),
            source_name=args.source_name or Path(args.path).name,
            dry_run=bool(args.dry_run),
        )
        result = ingest_file(args.workspace_id, args.path, options=options)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("status") != "failed" else 1

    if args.command == "export":
        from keprix.crm.ingestion.export import export_leads
        from keprix.crm.store import get_crm_store

        store = get_crm_store()
        leads = store.list_leads(args.workspace_id, limit=10_000)
        out = export_leads(leads, args.path, format=args.format)
        print(json.dumps({"path": str(out), "count": len(leads)}))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
