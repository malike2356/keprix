"""Agent migration CLI (Prompt 42)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from keprix.backend.migration.adapters import parse_source
from keprix.backend.migration.importer import MigrationImporter, preview_manifest
from keprix.backend.migration.manifest import AgentMigrationManifest
from keprix.backend.migration.n8n_converter import convert_n8n_workflow, load_n8n_export


def cmd_migrate_from(args: argparse.Namespace) -> int:
    source = args.source
    if source == "markdown":
        path = Path(args.notes_dir).expanduser()
    else:
        path = Path(args.export_dir).expanduser()
    if not path.exists():
        print(f"Path not found: {path}", file=sys.stderr)
        return 1
    manifest = parse_source(source, path)
    out = Path(args.out).expanduser()
    out.write_text(json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(f"Wrote manifest with {manifest.summary.item_count} items to {out}")
    return 0


def cmd_migrate_preview(args: argparse.Namespace) -> int:
    path = Path(args.manifest).expanduser()
    payload = json.loads(path.read_text(encoding="utf-8"))
    manifest = AgentMigrationManifest.model_validate(payload)
    print(preview_manifest(manifest))
    return 0


def cmd_migrate_apply(args: argparse.Namespace) -> int:
    path = Path(args.manifest).expanduser()
    payload = json.loads(path.read_text(encoding="utf-8"))
    manifest = AgentMigrationManifest.model_validate(payload)
    if args.approve_all:
        approved = [item.id for item in manifest.items]
    elif args.approve_ids:
        approved = [value.strip() for value in args.approve_ids.split(",") if value.strip()]
    else:
        print(preview_manifest(manifest))
        print("\nUse --approve-all or --approve-ids to apply without interactive prompts.")
        return 1
    if args.kinds:
        allowed = {kind.strip() for kind in args.kinds.split(",") if kind.strip()}
        approved = [item.id for item in manifest.items if item.id in approved and item.kind in allowed]
    importer = MigrationImporter()
    import asyncio

    result = asyncio.run(
        importer.apply(
            manifest,
            approved,
            workspace_id=args.workspace_id,
            user_id=args.user_id,
        )
    )
    print(
        f"Applied migration: imported={result.imported} skipped={result.skipped} failed={result.failed}"
    )
    for row in result.items:
        if row.status == "failed":
            print(f"  FAILED {row.id}: {row.error}", file=sys.stderr)
    return 0 if result.failed == 0 else 1


def cmd_migrate_from_n8n(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser()
    if not source.exists():
        print(f"Source not found: {source}", file=sys.stderr)
        return 1

    try:
        payload = load_n8n_export(source)
        result = convert_n8n_workflow(payload, playbook_id=args.id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Failed to convert n8n workflow: {exc}", file=sys.stderr)
        return 1

    summary = (
        f"Converted '{result.name}' -> playbook id '{result.playbook_id}' "
        f"({len(result.mapped_nodes)} mapped, {len(result.skipped_nodes)} skipped)"
    )

    if args.dry_run:
        print(summary)
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        if result.skipped_nodes:
            print("\nSkipped nodes:")
            for row in result.skipped_nodes:
                print(f"  - {row['name']} ({row['type']}): {row['reason']}")
        print("\n--- YAML ---\n")
        print(result.yaml_text, end="")
        return 0

    output_path: Path | None = None
    if args.output:
        output_path = Path(args.output).expanduser()
    elif args.output_dir:
        output_dir = Path(args.output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{result.playbook_id}.yml"
    else:
        print("Provide --output or --output-dir (or use --dry-run).", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.yaml_text, encoding="utf-8")
    print(f"Wrote playbook YAML to {output_path}")

    if args.report:
        report_path = output_path.with_name(f"{result.playbook_id}.migration-report.json")
        report_path.write_text(
            json.dumps(result.report_dict(), indent=2),
            encoding="utf-8",
        )
        print(f"Wrote migration report to {report_path}")

    if result.skipped_nodes:
        print(f"Note: {len(result.skipped_nodes)} node(s) skipped; review header comments in YAML.")
    return 0


def register_migrate_agent_subparsers(migrate_subparsers) -> None:
    from_parser = migrate_subparsers.add_parser("from", help="Build a migration manifest from a source export")
    from_parser.add_argument("source", choices=["hermes", "openclaw", "markdown", "generic"])
    from_parser.add_argument("--export-dir", help="Hermes/OpenClaw export directory")
    from_parser.add_argument("--notes-dir", help="Markdown notes directory")
    from_parser.add_argument("--out", required=True, help="Output manifest JSON path")
    from_parser.set_defaults(func=cmd_migrate_from)

    preview_parser = migrate_subparsers.add_parser("preview", help="Preview a migration manifest")
    preview_parser.add_argument("manifest", help="Path to migration.json")
    preview_parser.set_defaults(func=cmd_migrate_preview)

    apply_parser = migrate_subparsers.add_parser("apply", help="Apply an approved migration manifest")
    apply_parser.add_argument("manifest", help="Path to migration.json")
    apply_parser.add_argument("--approve-all", action="store_true")
    apply_parser.add_argument("--approve-ids", default="")
    apply_parser.add_argument("--kinds", default="", help="Comma-separated kinds filter with --approve-all")
    apply_parser.add_argument("--workspace-id", default="default")
    apply_parser.add_argument("--user-id", default="default")
    apply_parser.set_defaults(func=cmd_migrate_apply)

    n8n_parser = migrate_subparsers.add_parser(
        "from-n8n",
        help="Convert an exported n8n workflow JSON file to Keprix playbook YAML",
    )
    n8n_parser.add_argument("--source", required=True, help="Path to n8n workflow JSON export")
    n8n_parser.add_argument("--output", help="Write a single playbook .yml file")
    n8n_parser.add_argument("--output-dir", help="Write {playbook_id}.yml into this directory")
    n8n_parser.add_argument("--id", help="Override generated playbook id slug")
    n8n_parser.add_argument("--dry-run", action="store_true", help="Print YAML and summary only")
    n8n_parser.add_argument(
        "--report",
        action="store_true",
        help="Also write {playbook_id}.migration-report.json next to output",
    )
    n8n_parser.set_defaults(func=cmd_migrate_from_n8n)
