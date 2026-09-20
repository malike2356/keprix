"""``keprix portal`` used to onboard Nous Portal. That provider is gone."""
from __future__ import annotations

import sys


_REMOVED = (
    "Nous Portal was removed from Keprix.\n"
    "Use a BYOK provider instead: keprix model\n"
    "(DeepSeek, Anthropic, OpenRouter, and other API keys)."
)


def portal_command(args) -> int:
    """Refuse Nous Portal; point the user at BYOK setup."""
    print(_REMOVED, file=sys.stderr)
    return 1


def add_parser(subparsers) -> None:
    """Keep the command name so old scripts get a clear error instead of a crash."""
    portal_parser = subparsers.add_parser(
        "portal",
        help="Removed. Use keprix model with your own API key.",
        description=_REMOVED,
    )
    portal_parser.add_subparsers(dest="portal_command")
    portal_parser.set_defaults(func=lambda args: portal_command(args))
