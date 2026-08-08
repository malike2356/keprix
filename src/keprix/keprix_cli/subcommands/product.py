"""``keprix product`` subcommand parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable

_PRODUCT_CHOICES = (
    "petraclus",
    "abbis",
    "xeclone",
    "fleetz",
    "clinicom",
    "carina",
    "aiva",
)


def build_product_parser(subparsers: _SubParsersAction, *, cmd_product: Callable) -> None:
    parser = subparsers.add_parser(
        "product",
        help="Product sidecar provision, registry, Scout register, and conformance",
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

    listing = sub.add_parser("list", help="List registered products (Scout metadata)")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(func=cmd_product)

    provision = sub.add_parser("provision", help="Declarative product sidecar provision")
    provision.add_argument("product_id", choices=_PRODUCT_CHOICES)
    provision.add_argument("--plan", action="store_true", help="Show plan without applying")
    provision.add_argument("--status", action="store_true", help="Show latest provision receipt")
    provision.add_argument("--activate", action="store_true", help="Enable pack after provision")
    provision.add_argument("--version", default="1.0.0")
    provision.add_argument("--legacy-clinicom", action="store_true", help="Use clinicom integration readiness path")
    provision.add_argument("--json", action="store_true")
    provision.set_defaults(func=cmd_product)

    plan = sub.add_parser("plan", help="Show provision plan")
    plan.add_argument("product_id", choices=_PRODUCT_CHOICES)
    plan.set_defaults(func=cmd_product)

    status = sub.add_parser("status", help="Show pack health and provision receipt")
    status.add_argument("product_id", choices=_PRODUCT_CHOICES)
    status.set_defaults(func=cmd_product)

    upgrade = sub.add_parser("upgrade", help="Upgrade installed pack version")
    upgrade.add_argument("product_id", choices=_PRODUCT_CHOICES)
    upgrade.add_argument("--version", required=True)
    upgrade.set_defaults(func=cmd_product)

    rollback = sub.add_parser("rollback", help="Rollback to last-known-good pack")
    rollback.add_argument("product_id", choices=_PRODUCT_CHOICES)
    rollback.set_defaults(func=cmd_product)

    disable = sub.add_parser("disable", help="Disable product pack kill switch")
    disable.add_argument("product_id", choices=_PRODUCT_CHOICES)
    disable.set_defaults(func=cmd_product)

    remove = sub.add_parser("remove", help="Remove a non-platform fixture/product pack")
    remove.add_argument("product_id", choices=_PRODUCT_CHOICES)
    remove.set_defaults(func=cmd_product)

    conformance = sub.add_parser("conformance", help="Run foundation conformance suite")
    conformance.set_defaults(func=cmd_product)
