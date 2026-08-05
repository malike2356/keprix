"""Vault CLI parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_vault_parser(
    subparsers: _SubParsersAction,
    *,
    cmd_vault: Callable,
) -> None:
    parser = subparsers.add_parser("vault", help="Initialize and validate local markdown vaults")
    sub = parser.add_subparsers(dest="vault_command", required=True)

    sub.add_parser("list-packs", help="List available vault starter packs").set_defaults(func=cmd_vault)

    init = sub.add_parser("init", help="Initialize a vault from a starter pack")
    init.add_argument("--pack", default="obsidian-starter")
    init.add_argument("--path", required=True)
    init.add_argument("--overwrite", action="store_true")
    init.set_defaults(func=cmd_vault)

    validate = sub.add_parser("validate", help="Validate a vault manifest and folder tree")
    validate.add_argument("--path", required=True)
    validate.set_defaults(func=cmd_vault)

    doctor = sub.add_parser("doctor", help="Report vault health and diagnostics")
    doctor.add_argument("--path", required=True)
    doctor.set_defaults(func=cmd_vault)

    migrate = sub.add_parser("migrate-workspace", help="Copy workspace markdown files into a vault")
    migrate.add_argument("--from", dest="from_path", required=True)
    migrate.add_argument("--to", dest="to_path", required=True)
    migrate.set_defaults(func=cmd_vault)

    render = sub.add_parser("render-template", help="Render a vault note template")
    render.add_argument("--path", required=True)
    render.add_argument("--template", required=True)
    render.add_argument("--output")
    render.set_defaults(func=cmd_vault)

    audit = sub.add_parser("audit", help="Audit credential vault expiry and rotation")
    audit.add_argument("--expiring", dest="expiring_days", type=int)
    audit.add_argument("--rotation-due", action="store_true")
    audit.add_argument("--json", action="store_true")
    audit.set_defaults(func=cmd_vault)

    ensure = sub.add_parser("ensure-default", help="Create the single default vault if missing")
    ensure.set_defaults(func=cmd_vault)
