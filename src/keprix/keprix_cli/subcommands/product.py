"""``keprix product`` subcommand parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_product_parser(subparsers: _SubParsersAction, *, cmd_product: Callable) -> None:
    parser = subparsers.add_parser(
        "product",
        help="Register Keprix-built products for Scout monitoring",
    )
    sub = parser.add_subparsers(dest="product_command", required=True)

    register = sub.add_parser("register", help="Register a product with Scout metadata")
    register.add_argument("product_id", help="Product slug, e.g. abbis")
    register.add_argument("--scout-enabled", choices=("true", "false"), default="true")
    register.add_argument("--personas", default="", help="Comma-separated persona list")
    register.add_argument("--tools", default="", help="Comma-separated tool list")
    register.add_argument("--security-policy", default="standard")
    register.add_argument("--json", action="store_true")
    register.set_defaults(func=cmd_product)

    listing = sub.add_parser("list", help="List registered products")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(func=cmd_product)

    provision = sub.add_parser("provision", help="Validate and prepare a product integration")
    provision.add_argument("product_id", choices=("clinicom",))
    provision.add_argument("--plan", action="store_true", help="Show checks without writing a receipt")
    provision.add_argument("--status", action="store_true", help="Show the latest provision receipt")
    provision.add_argument("--json", action="store_true")
    provision.set_defaults(func=cmd_product)
