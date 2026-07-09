"""CLI handlers for ``keprix proxy`` credential injection commands."""

from __future__ import annotations

import argparse
import multiprocessing
import sys
from typing import Any

from keprix.proxy.config import load_proxy_config
from keprix.proxy.doctor import run_doctor
from keprix.proxy.env_writer import print_proxy_env, write_proxy_env
from keprix.proxy.migrate import migrate_vault_from_env
from keprix.proxy.pidfile import is_running, read_pid, stop_running, write_pid
from keprix.proxy.routes import add_route, list_routes, remove_route
from keprix.proxy.server import run_proxy_server_sync
from keprix.proxy.setup_wizard import run_setup_wizard
from keprix.proxy.verify import verify_routes


def _daemon_target() -> None:
    write_pid()
    run_proxy_server_sync()


def cmd_credential_proxy_start(args: Any) -> int:
    if is_running():
        print(f"Credential proxy already running (pid {read_pid()})", file=sys.stderr)
        return 1
    daemon = bool(getattr(args, "daemon", False))
    if daemon:
        process = multiprocessing.Process(target=_daemon_target, daemon=True)
        process.start()
        write_pid(process.pid)
        print(f"Credential proxy started in background (pid {process.pid})")
        return 0
    write_pid()
    try:
        run_proxy_server_sync()
    except KeyboardInterrupt:
        print("\nCredential proxy stopped", file=sys.stderr)
    return 0


def cmd_credential_proxy_stop(_args: Any) -> int:
    if stop_running():
        print("Credential proxy stopped")
        return 0
    print("Credential proxy is not running", file=sys.stderr)
    return 1


def cmd_credential_proxy_status(_args: Any) -> int:
    if is_running():
        print(f"Credential proxy running (pid {read_pid()})")
        return 0
    print("Credential proxy is not running")
    return 1


def cmd_credential_proxy_setup(_args: Any) -> int:
    config = run_setup_wizard()
    print(f"Wrote proxy config with {len(config.routes)} routes")
    print(f"Vault provider: {config.vault}")
    print("Run: keprix proxy doctor")
    return 0


def cmd_credential_proxy_doctor(_args: Any) -> int:
    report = run_doctor()
    for line in report.lines:
        print(line)
    return 0 if report.ok else 1


def cmd_credential_proxy_env(_args: Any) -> int:
    print(print_proxy_env(load_proxy_config()))
    return 0


def cmd_credential_proxy_migrate_vault(_args: Any) -> int:
    result = migrate_vault_from_env()
    if result.migrated:
        print("Migrated env keys:", ", ".join(result.migrated))
    if result.skipped:
        print("Skipped env keys:", ", ".join(result.skipped))
    write_proxy_env(load_proxy_config())
    return 0


def cmd_credential_proxy_verify(_args: Any) -> int:
    report = verify_routes()
    for line in report.lines:
        print(line)
    return 0 if report.ok else 1


def cmd_credential_proxy_route_add(args: Any) -> int:
    add_route(
        host=args.host,
        header_name=args.header_name,
        secret_ref=args.secret_ref,
        scheme=getattr(args, "scheme", None),
    )
    print(f"Added route for {args.host}")
    return 0


def cmd_credential_proxy_route_list(_args: Any) -> int:
    routes = list_routes()
    if not routes:
        print("No routes configured")
        return 0
    for route in routes:
        scheme = f" scheme={route.scheme}" if route.scheme else ""
        print(f"{route.host} -> {route.header_name} ({route.secret_ref}){scheme}")
    return 0


def cmd_credential_proxy_route_rm(args: Any) -> int:
    remove_route(args.host)
    print(f"Removed route for {args.host}")
    return 0


def dispatch_credential_proxy(args: Any) -> int:
    sub = getattr(args, "proxy_command", None)
    if sub == "start" and getattr(args, "provider", None) in (None, ""):
        return cmd_credential_proxy_start(args)
    if sub == "start" and getattr(args, "provider", None) in {"nous", "xai"}:
        from keprix_cli.proxy.cli import cmd_proxy_start

        return cmd_proxy_start(args)
    handlers = {
        "setup": cmd_credential_proxy_setup,
        "stop": cmd_credential_proxy_stop,
        "status": cmd_credential_proxy_status,
        "doctor": cmd_credential_proxy_doctor,
        "env": cmd_credential_proxy_env,
        "migrate-vault": cmd_credential_proxy_migrate_vault,
        "verify": cmd_credential_proxy_verify,
    }
    handler = handlers.get(sub or "")
    if handler:
        return handler(args)
    if sub == "route":
        route_cmd = getattr(args, "route_command", None)
        if route_cmd == "add":
            return cmd_credential_proxy_route_add(args)
        if route_cmd == "list":
            return cmd_credential_proxy_route_list(args)
        if route_cmd == "rm":
            return cmd_credential_proxy_route_rm(args)
    if sub in {"providers", "list"}:
        from keprix_cli.proxy.cli import cmd_proxy_list_providers

        return cmd_proxy_list_providers(args)
    if sub == "oauth":
        oauth_cmd = getattr(args, "oauth_command", None)
        from keprix_cli.proxy.cli import cmd_proxy_list_providers, cmd_proxy_start, cmd_proxy_status

        if oauth_cmd == "start":
            return cmd_proxy_start(args)
        if oauth_cmd == "status":
            return cmd_proxy_status(args)
        if oauth_cmd in {"providers", "list"}:
            return cmd_proxy_list_providers(args)
    _print_help()
    return 0


def _print_help() -> None:
    print(
        "keprix proxy — credential injection proxy (Cordon pattern)\n"
        "\n"
        "Credential proxy:\n"
        "  keprix proxy setup\n"
        "  keprix proxy start [--daemon]\n"
        "  keprix proxy stop\n"
        "  keprix proxy status\n"
        "  keprix proxy doctor\n"
        "  keprix proxy env\n"
        "  keprix proxy migrate-vault\n"
        "  keprix proxy verify\n"
        "  keprix proxy route add --host HOST --header-name NAME --secret-ref REF\n"
        "  keprix proxy route list\n"
        "  keprix proxy route rm --host HOST\n"
        "\n"
        "OAuth upstream proxy (legacy):\n"
        "  keprix proxy oauth start [--provider nous|xai]\n"
        "  keprix proxy oauth status\n"
        "  keprix proxy oauth providers\n"
        "  keprix proxy start --provider nous|xai\n",
        file=sys.stderr,
    )


def build_credential_proxy_parsers(proxy_subparsers: argparse._SubParsersAction) -> None:
    proxy_subparsers.add_parser("setup", help="Interactive credential proxy setup")
    start = proxy_subparsers.add_parser("start", help="Start credential or OAuth proxy")
    start.add_argument("--daemon", action="store_true", help="Run credential proxy in background")
    start.add_argument(
        "--provider",
        default=None,
        help="OAuth upstream provider (nous|xai). Omit for credential injection proxy.",
    )
    proxy_subparsers.add_parser("stop", help="Stop credential proxy")
    proxy_subparsers.add_parser("status", help="Show credential proxy status")
    proxy_subparsers.add_parser("doctor", help="Run credential proxy diagnostics")
    proxy_subparsers.add_parser("env", help="Print proxy environment exports")
    proxy_subparsers.add_parser("migrate-vault", help="Migrate .env keys into proxy vault")
    proxy_subparsers.add_parser("verify", help="Verify configured routes resolve secrets")

    route_parser = proxy_subparsers.add_parser("route", help="Manage proxy routes")
    route_sub = route_parser.add_subparsers(dest="route_command")
    route_add = route_sub.add_parser("add", help="Add a proxy route")
    route_add.add_argument("--host", required=True)
    route_add.add_argument("--header-name", required=True)
    route_add.add_argument("--secret-ref", required=True)
    route_add.add_argument("--scheme", default=None)
    route_sub.add_parser("list", help="List proxy routes")
    route_rm = route_sub.add_parser("rm", help="Remove a proxy route")
    route_rm.add_argument("--host", required=True)

    oauth_parser = proxy_subparsers.add_parser("oauth", help="OAuth upstream proxy commands")
    oauth_sub = oauth_parser.add_subparsers(dest="oauth_command")
    oauth_start = oauth_sub.add_parser("start", help="Start OAuth upstream proxy")
    oauth_start.add_argument("--provider", default="nous")
    oauth_start.add_argument("--host", default=None)
    oauth_start.add_argument("--port", type=int, default=None)
    oauth_sub.add_parser("status", help="OAuth upstream adapter status")
    oauth_sub.add_parser("providers", help="List OAuth upstream providers")
