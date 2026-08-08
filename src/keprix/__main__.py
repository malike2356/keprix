"""Keprix package entrypoint."""

from __future__ import annotations

import json
import sys


def _print_version(*, as_json: bool = False) -> int:
    from keprix_cli import __release_date__, __version__

    if as_json:
        from keprix.release_manifest import current_identity

        payload = current_identity().as_dict()
        payload["release_date"] = __release_date__
        print(json.dumps(payload, sort_keys=True))
        return 0
    print(f"Keprix {__version__} ({__release_date__})")
    return 0


def _run_init(force: bool = False) -> int:
    from keprix.keys.developer_identity import create_developer_identity, get_identity_status

    try:
        answer = input("Are you the owner of this installation? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 1
    if answer not in {"y", "yes"}:
        print("Developer identity was not created.")
        return 1
    try:
        status = create_developer_identity(force=force)
    except FileExistsError as exc:
        print(str(exc))
        return 1
    print(f"Developer identity created for {status['product']}.")
    print(f"Identity directory: {status['identity_dir']}")
    print(f"Valid: {status['valid']}")
    return 0


def _run_identity_status() -> int:
    from keprix.keys.developer_identity import get_identity_status
    from keprix.keys.local_access import effective_access_level

    status = get_identity_status()
    print(f"Product: {status['product']}")
    print(f"Valid: {status['valid']}")
    print(f"Access level: {effective_access_level()}")
    print(f"Identity directory: {status['identity_dir']}")
    if status.get("created_at"):
        print(f"Created at: {status['created_at']}")
    return 0 if status["valid"] else 1


def _run_identity_revoke() -> int:
    from keprix.keys.developer_identity import revoke_developer_identity

    try:
        answer = input("Revoke developer identity on this machine? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 1
    if answer not in {"y", "yes"}:
        print("No changes made.")
        return 0
    revoke_developer_identity()
    print("Developer identity revoked.")
    return 0


def _run_builder(argv: list[str]) -> int:
    import argparse

    from keprix.keprix_cli import builder_commands

    parser = argparse.ArgumentParser(prog="keprix builder")
    sub = parser.add_subparsers(dest="builder_command", required=True)

    sub.add_parser("list", help="List discovered projects").set_defaults(func=builder_commands.cmd_builder_list)

    analyse = sub.add_parser("analyse", help="Analyse a project")
    analyse.add_argument("name")
    analyse.set_defaults(func=builder_commands.cmd_builder_analyse)

    build = sub.add_parser("build", help="Run a build job")
    build.add_argument("name")
    build.add_argument("instruction")
    build.set_defaults(func=builder_commands.cmd_builder_build)

    scaffold = sub.add_parser("scaffold", help="Scaffold a new project")
    scaffold.add_argument("template")
    scaffold.add_argument("name")
    scaffold.add_argument("--path", default="/tmp/keprix-scaffolds")
    scaffold.set_defaults(func=builder_commands.cmd_builder_scaffold)

    status = sub.add_parser("status", help="Job status")
    status.add_argument("job_id")
    status.set_defaults(func=builder_commands.cmd_builder_status)

    logs = sub.add_parser("logs", help="Job logs")
    logs.add_argument("job_id")
    logs.set_defaults(func=builder_commands.cmd_builder_logs)

    deploy = sub.add_parser("deploy", help="Deploy project")
    deploy.add_argument("name")
    deploy.add_argument("--target", choices=["lampp", "docker"], default="lampp")
    deploy.set_defaults(func=builder_commands.cmd_builder_deploy)

    args = parser.parse_args(argv)
    return int(args.func(args))


def _run_start(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Start the Keprix API server")
    parser.add_argument("--port", type=int, default=3333)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    import uvicorn

    uvicorn.run("keprix.api.main:app", host=args.host, port=args.port, reload=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"-V", "--version", "version"}:
        return _print_version(as_json="--json" in argv[1:])

    if not argv:
        import fire
        from keprix.cli import main as keprix_main

        fire.Fire(keprix_main)
        return 0

    from keprix.installer.cli import INSTALLER_COMMANDS

    if argv[0] in INSTALLER_COMMANDS:
        return INSTALLER_COMMANDS[argv[0]](argv[1:])

    if argv[0] == "start":
        return INSTALLER_COMMANDS["start"](argv[1:])

    if argv[0] == "init":
        force = "--force" in argv[1:]
        return _run_init(force=force)

    if argv[0] == "identity":
        if len(argv) < 2 or argv[1] in {"-h", "--help"}:
            print("Usage: keprix identity {status|revoke}")
            return 0
        if argv[1] == "status":
            return _run_identity_status()
        if argv[1] == "revoke":
            return _run_identity_revoke()
        print(f"Unknown identity command: {argv[1]}")
        return 2

    if argv[0] == "builder":
        return _run_builder(argv[1:])

    if argv[0] == "tui":
        from keprix.tui.cli import run_tui

        return run_tui(argv[1:])

    if argv[0] == "upstream":
        from keprix.keprix_cli.main import main as cli_main

        sys.argv = [sys.argv[0], *argv]
        cli_main()
        return 0

    import fire
    from keprix.cli import main as keprix_main

    fire.Fire(keprix_main)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
