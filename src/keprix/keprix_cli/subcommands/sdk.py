"""App Foundation SDK CLI subcommand parsers."""

from __future__ import annotations

from typing import Callable


def build_sdk_parser(subparsers, *, cmd_list: Callable, cmd_show: Callable, cmd_unregister: Callable, cmd_test: Callable) -> None:
    sdk_parser = subparsers.add_parser(
        "sdk",
        help="Manage App Foundation SDK registrations",
        description="List, inspect, test, and unregister SDK apps.",
    )
    sdk_sub = sdk_parser.add_subparsers(dest="sdk_command", required=True)

    list_parser = sdk_sub.add_parser("list", help="List registered SDK apps")
    list_parser.set_defaults(func=cmd_list)

    show_parser = sdk_sub.add_parser("show", help="Show app schema and metadata")
    show_parser.add_argument("app_id", help="Registered app ID")
    show_parser.set_defaults(func=cmd_show)

    unregister_parser = sdk_sub.add_parser("unregister", help="Unregister an SDK app")
    unregister_parser.add_argument("app_id", help="Registered app ID")
    unregister_parser.set_defaults(func=cmd_unregister)

    test_parser = sdk_sub.add_parser("test", help="Interactive NL to ActionPlan tester")
    test_parser.add_argument("app_id", help="Registered app ID")
    test_parser.set_defaults(func=cmd_test)
