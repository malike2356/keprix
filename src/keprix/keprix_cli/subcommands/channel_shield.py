"""``keprix channel-shield`` (and ``email-shield`` alias) subcommand parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_channel_shield_parser(subparsers: _SubParsersAction, *, cmd_channel_shield: Callable) -> None:
    parser = subparsers.add_parser(
        "channel-shield",
        help="Channel Shield doctor, adapters, and fixture E2E",
        description="Shared inbound protection plane across email and messaging channels.",
    )
    sub = parser.add_subparsers(dest="channel_shield_command", required=True)

    doctor = sub.add_parser("doctor", help="Run Channel Shield health checks")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_channel_shield)

    adapters = sub.add_parser("adapters", help="List adapter health")
    adapters.add_argument("--json", action="store_true")
    adapters.set_defaults(func=cmd_channel_shield)

    e2e = sub.add_parser("e2e", help="Run fixture E2E for one channel or all")
    e2e.add_argument(
        "--channel",
        default="all",
        help="email|slack|teams|telegram|whatsapp|discord|sms|web|all",
    )
    e2e.add_argument("--json", action="store_true")
    e2e.set_defaults(func=cmd_channel_shield)


def build_email_shield_parser(subparsers: _SubParsersAction, *, cmd_channel_shield: Callable) -> None:
    """Compatibility alias: email-shield -> channel-shield."""
    parser = subparsers.add_parser(
        "email-shield",
        help="Alias for channel-shield (email-focused)",
        description="Compatibility alias. Prefer: keprix channel-shield ...",
    )
    sub = parser.add_subparsers(dest="channel_shield_command", required=True)

    doctor = sub.add_parser("doctor", help="Run Channel Shield health checks")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_channel_shield, channel_shield_alias="email")

    adapters = sub.add_parser("adapters", help="List adapter health")
    adapters.add_argument("--json", action="store_true")
    adapters.set_defaults(func=cmd_channel_shield, channel_shield_alias="email")

    e2e = sub.add_parser("e2e", help="Run email adapter fixture E2E")
    e2e.add_argument("--channel", default="email")
    e2e.add_argument("--json", action="store_true")
    e2e.set_defaults(func=cmd_channel_shield, channel_shield_alias="email")
