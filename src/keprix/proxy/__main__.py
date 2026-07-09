"""Standalone CLI for keprix-proxy."""

from __future__ import annotations

import sys

from keprix.proxy.cli_handlers import dispatch_credential_proxy


class Args:
    proxy_command: str | None
    provider: str | None
    daemon: bool
    host: str | None
    port: int | None
    route_command: str | None
    oauth_command: str | None
    header_name: str | None
    secret_ref: str | None
    scheme: str | None


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = Args()
    args.provider = None
    args.daemon = False
    args.host = None
    args.port = None
    args.route_command = None
    args.oauth_command = None
    args.header_name = None
    args.secret_ref = None
    args.scheme = None

    if not argv or argv[0] in {"-h", "--help", "help"}:
        from keprix.proxy.cli_handlers import _print_help

        _print_help()
        return 0

    command = argv[0]
    rest = argv[1:]
    if command == "route" and rest:
        args.proxy_command = "route"
        args.route_command = rest[0]
        rest = rest[1:]
    elif command == "oauth" and rest:
        args.proxy_command = "oauth"
        args.oauth_command = rest[0]
        rest = rest[1:]
    else:
        args.proxy_command = command

    index = 0
    while index < len(rest):
        token = rest[index]
        if token == "--daemon":
            args.daemon = True
        elif token == "--provider" and index + 1 < len(rest):
            args.provider = rest[index + 1]
            index += 1
        elif token == "--host" and index + 1 < len(rest):
            if args.proxy_command == "route" and args.route_command == "add":
                args.host = rest[index + 1]
            else:
                args.host = rest[index + 1]
            index += 1
        elif token == "--header-name" and index + 1 < len(rest):
            args.header_name = rest[index + 1]
            index += 1
        elif token == "--secret-ref" and index + 1 < len(rest):
            args.secret_ref = rest[index + 1]
            index += 1
        elif token == "--scheme" and index + 1 < len(rest):
            args.scheme = rest[index + 1]
            index += 1
        index += 1

    return dispatch_credential_proxy(args)


if __name__ == "__main__":
    raise SystemExit(main())
