"""``keprix dashboard`` subcommand parser.

Extracted verbatim from ``keprix_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

import argparse
from typing import Callable


def build_dashboard_parser(
    subparsers, *, cmd_dashboard: Callable, cmd_dashboard_register: Callable,
    cmd_dashboard_service: Callable,
) -> None:
    """Attach the ``dashboard`` subcommand (and its ``register`` action)."""
    # =========================================================================
    # dashboard command
    # =========================================================================
    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Start the web UI dashboard",
        description="Launch the Keprix web dashboard for managing config, API keys, and sessions",
    )
    dashboard_parser.add_argument(
        "--port", type=int, default=9119, help="Port (default 9119, 0 for auto-assign by OS)"
    )
    dashboard_parser.add_argument(
        "--host", default="127.0.0.1", help="Host (default 127.0.0.1)"
    )
    dashboard_parser.add_argument(
        "--no-open", action="store_true", help="Don't open browser automatically"
    )
    dashboard_parser.add_argument(
        "--insecure",
        action="store_true",
        help="Allow binding to non-localhost (DANGEROUS: exposes API keys on the network)",
    )
    dashboard_parser.add_argument(
        "--skip-build",
        action="store_true",
        help=(
            "Skip the web UI build step and serve the existing dist directly. "
            "Useful for non-interactive contexts (Windows Scheduled Tasks, CI) "
            "where npm may not be available. Pre-build with: cd web && npm run build"
        ),
    )
    dashboard_parser.add_argument(
        "--isolated",
        action="store_true",
        help=(
            "When launched from a named profile (e.g. `worker dashboard`), run "
            "a dedicated dashboard server scoped to that profile instead of "
            "routing to the machine dashboard. Default behavior is unified: "
            "profile launches attach to (or start) ONE machine-level dashboard "
            "and preselect the profile in the UI's profile switcher."
        ),
    )
    # Internal flag set by the unified-launch re-exec (cmd_dashboard) to
    # preselect the launching profile in the SPA switcher. Hidden from
    # --help: users get this behavior automatically via `<profile> dashboard`.
    dashboard_parser.add_argument(
        "--open-profile",
        dest="open_profile",
        default="",
        help=argparse.SUPPRESS,
    )
    # Lifecycle flags — process-table scan (stray foreground `keprix dashboard`
    # processes). Distinct from `keprix dashboard stop` / `status`, which talk
    # to the systemd/launchd unit created by `keprix dashboard install`.
    # If both a flag and a start-a-server option are passed, --stop / --status
    # win because they exit before the server is started.
    dashboard_parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop all running keprix dashboard processes and exit",
    )
    dashboard_parser.add_argument(
        "--status",
        action="store_true",
        help="List running keprix dashboard processes and exit",
    )
    # Backward-compat shim: older Keprix desktop app shells (<= 0.15.x) spawn the
    # backend as `keprix dashboard --no-open --tui --host ... --port ...`. The
    # `--tui` flag was removed from this subcommand in cae6b5486 (embedded chat is
    # always on now). When a user's CLI updates past that commit but their desktop
    # app binary has not, argparse used to hard-error with "unrecognized arguments:
    # --tui" and exit(2) — the backend died before becoming ready and the GUI just
    # showed "Keprix couldn't start" with no actionable cause. Accept and silently
    # ignore the flag so an old app + new CLI degrades gracefully instead of
    # bricking. Hidden from --help; safe to delete once the floor app version is
    # well past 0.16.0.
    dashboard_parser.add_argument(
        "--tui",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    dashboard_parser.set_defaults(func=cmd_dashboard)

    # `keprix dashboard register` — register a self-hosted dashboard OAuth
    # client with Nous Portal and write the client_id into ~/.keprix/.env.
    # Nested subparser so bare `keprix dashboard` keeps launching the server
    # (set_defaults(func=cmd_dashboard) above remains the default).
    dashboard_subparsers = dashboard_parser.add_subparsers(
        dest="dashboard_subcommand"
    )
    dashboard_register_parser = dashboard_subparsers.add_parser(
        "register",
        help="Removed. Dashboard login is local basic auth or self-hosted OIDC.",
        description=(
            "Nous Portal dashboard registration was removed from Keprix. "
            "Use KEPRIX_ADMIN_EMAIL / KEPRIX_ADMIN_PASSWORD (basic auth) "
            "or a self-hosted OIDC provider."
        ),
    )
    dashboard_register_parser.add_argument(
        "--name",
        default=None,
        help="Human-readable label for the dashboard (default: an auto-generated name)",
    )
    dashboard_register_parser.add_argument(
        "--redirect-uri",
        dest="redirect_uri",
        default=None,
        help=(
            "Optional public HTTPS OAuth redirect URI for the dashboard, e.g. "
            "https://keprix.example.com/auth/callback. Omit for localhost-only use."
        ),
    )
    dashboard_register_parser.add_argument(
        "--portal-url",
        dest="portal_url",
        default=None,
        help="Ignored. Nous Portal registration was removed.",
    )
    dashboard_register_parser.set_defaults(func=cmd_dashboard_register)

    def _add_system_flag(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--system",
            action="store_true",
            help="Target the Linux system-level dashboard service",
        )

    dashboard_install = dashboard_subparsers.add_parser(
        "install",
        help="Install dashboard as a systemd/launchd background service",
    )
    dashboard_install.add_argument("--force", action="store_true", help="Force reinstall")
    _add_system_flag(dashboard_install)
    dashboard_install.add_argument(
        "--port", type=int, default=9119, help="Backend port (default 9119)"
    )
    dashboard_install.add_argument(
        "--host", default="127.0.0.1", help="Bind host (default 127.0.0.1)"
    )
    dashboard_install.add_argument(
        "--frontend-port",
        dest="frontend_port",
        type=int,
        default=9120,
        help="Pinned Next.js UI port (default 9120)",
    )
    dashboard_install.add_argument(
        "--run-as-user",
        dest="run_as_user",
        help="User account the Linux system service should run as",
    )
    dashboard_install.add_argument(
        "--no-start",
        action="store_true",
        help="Write and enable the unit without starting it now",
    )
    dashboard_install.set_defaults(func=cmd_dashboard_service)

    dashboard_uninstall = dashboard_subparsers.add_parser(
        "uninstall", help="Uninstall dashboard service"
    )
    _add_system_flag(dashboard_uninstall)
    dashboard_uninstall.set_defaults(func=cmd_dashboard_service)

    dashboard_start = dashboard_subparsers.add_parser(
        "start", help="Start the installed dashboard background service"
    )
    _add_system_flag(dashboard_start)
    dashboard_start.set_defaults(func=cmd_dashboard_service)

    dashboard_stop_svc = dashboard_subparsers.add_parser(
        "stop", help="Stop the installed dashboard background service"
    )
    _add_system_flag(dashboard_stop_svc)
    dashboard_stop_svc.set_defaults(func=cmd_dashboard_service)

    dashboard_restart = dashboard_subparsers.add_parser(
        "restart", help="Restart the installed dashboard background service"
    )
    _add_system_flag(dashboard_restart)
    dashboard_restart.set_defaults(func=cmd_dashboard_service)

    dashboard_status_svc = dashboard_subparsers.add_parser(
        "status", help="Show dashboard service status"
    )
    _add_system_flag(dashboard_status_svc)
    dashboard_status_svc.set_defaults(func=cmd_dashboard_service)
