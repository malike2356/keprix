"""``keprix scout`` subcommand parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_scout_parser(subparsers: _SubParsersAction, *, cmd_scout: Callable) -> None:
    parser = subparsers.add_parser(
        "scout",
        help="Scout connectivity and integration tests",
        description="Ping Scout, send probe signals, and verify command handling.",
    )
    sub = parser.add_subparsers(dest="scout_command", required=True)

    ping = sub.add_parser("ping", help="Test Scout endpoint reachability")
    ping.add_argument("--json", action="store_true")
    ping.set_defaults(func=cmd_scout)

    test_signal = sub.add_parser("test-signal", help="Send a probe signal to Scout")
    test_signal.add_argument("--json", action="store_true")
    test_signal.set_defaults(func=cmd_scout)

    test_command = sub.add_parser("test-command", help="Exercise local Scout command handling")
    test_command.add_argument("--json", action="store_true")
    test_command.set_defaults(func=cmd_scout)

    status = sub.add_parser("status", help="Show Scout integration status")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_scout)

    integration = sub.add_parser("integration-test", help="Run end-to-end Scout integration test")
    integration.add_argument("--json", action="store_true")
    integration.set_defaults(func=cmd_scout)

    signals = sub.add_parser("signals", help="Show recent signal metrics")
    signals.add_argument("--product")
    signals.add_argument("--24h", dest="period_24h", action="store_true")
    signals.add_argument("--json", action="store_true")
    signals.set_defaults(func=cmd_scout)

    suspend = sub.add_parser("suspend", help="Block a session locally")
    suspend.add_argument("--product")
    suspend.add_argument("--session", required=True)
    suspend.add_argument("--json", action="store_true")
    suspend.set_defaults(func=cmd_scout)

    quarantine = sub.add_parser("quarantine", help="Quarantine a tool")
    quarantine.add_argument("--tool", required=True)
    quarantine.add_argument("--product")
    quarantine.add_argument("--json", action="store_true")
    quarantine.set_defaults(func=cmd_scout)

    block_egress = sub.add_parser("block-egress", help="Block all egress")
    block_egress.add_argument("--product")
    block_egress.add_argument("--json", action="store_true")
    block_egress.set_defaults(func=cmd_scout)

    sandbox = sub.add_parser("set-sandbox", help="Apply sandbox policy to a product")
    sandbox.add_argument("--mode", required=True, choices=["docker", "host", "session_only"])
    sandbox.add_argument("--product", required=True)
    sandbox.add_argument("--json", action="store_true")
    sandbox.set_defaults(func=cmd_scout)
