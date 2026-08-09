"""``keprix crm-ingest`` thin CLI (Prompt 621)."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_crm_ingest_parser(
    subparsers: _SubParsersAction,
    *,
    cmd_crm_ingest: Callable,
) -> None:
    parser = subparsers.add_parser(
        "crm-ingest",
        help="Canonical CRM lead spreadsheet import/export",
    )
    sub = parser.add_subparsers(dest="crm_ingest_command", required=True)

    preview = sub.add_parser("preview", help="Preview header mapping")
    preview.add_argument("path")
    preview.add_argument("--workspace-id", default="default")
    preview.add_argument("--limit", type=int, default=5)
    preview.set_defaults(func=cmd_crm_ingest)

    import_p = sub.add_parser("import", help="Import leads from a spreadsheet")
    import_p.add_argument("path")
    import_p.add_argument("--workspace-id", required=True)
    import_p.add_argument("--overwrite", action="store_true")
    import_p.add_argument("--source-name", default=None)
    import_p.add_argument("--dry-run", action="store_true")
    import_p.set_defaults(func=cmd_crm_ingest)

    export_p = sub.add_parser("export", help="Export leads (xlsx default)")
    export_p.add_argument("path")
    export_p.add_argument("--workspace-id", required=True)
    export_p.add_argument("--format", choices=["xlsx", "csv"], default="xlsx")
    export_p.set_defaults(func=cmd_crm_ingest)
