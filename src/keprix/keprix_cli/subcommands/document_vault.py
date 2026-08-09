"""``keprix document-vault`` thin CLI (Prompt 645)."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_document_vault_parser(
    subparsers: _SubParsersAction,
    *,
    cmd_document_vault: Callable,
) -> None:
    parser = subparsers.add_parser(
        "document-vault",
        help="Document Vault inventory, flags, and adapter registry",
    )
    sub = parser.add_subparsers(dest="document_vault_command", required=True)

    inv = sub.add_parser("inventory", help="Read-only surface and checksum audit")
    inv.add_argument("--workspace-id", default="local")
    inv.set_defaults(func=cmd_document_vault)

    flags = sub.add_parser("flags", help="Show Document Vault feature flags")
    flags.set_defaults(func=cmd_document_vault)

    adapters = sub.add_parser("adapters", help="List compatibility adapter specs")
    adapters.set_defaults(func=cmd_document_vault)
