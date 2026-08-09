"""Handlers for ``keprix document-vault`` (Prompt 645)."""

from __future__ import annotations

import json
import sys


def cmd_document_vault(args) -> int:
    command = getattr(args, "document_vault_command", None)
    if command == "inventory":
        from keprix.document_vault.inventory import build_inventory_report

        report = build_inventory_report(
            str(getattr(args, "workspace_id", "local") or "local"),
            dry_run=True,
        )
        sys.stdout.write(json.dumps(report, indent=2, default=str) + "\n")
        return 0 if report.get("mutated") is False else 2

    if command == "flags":
        from keprix.document_vault.flags import load_flags

        sys.stdout.write(json.dumps(load_flags().as_env_map(), indent=2) + "\n")
        return 0

    if command == "adapters":
        from keprix.document_vault.compatibility import list_adapters

        sys.stdout.write(json.dumps(list_adapters(), indent=2) + "\n")
        return 0

    if command == "migrate":
        from keprix.document_vault.migrate import migrate_from_workspace_repo

        dry = not bool(getattr(args, "write", False))
        result = migrate_from_workspace_repo(
            str(getattr(args, "workspace_id", "local") or "local"),
            dry_run=dry,
        )
        sys.stdout.write(json.dumps(result, indent=2, default=str) + "\n")
        return 0 if result.get("ok", True) else 1

    sys.stderr.write(f"unknown document-vault command: {command}\n")
    return 2
