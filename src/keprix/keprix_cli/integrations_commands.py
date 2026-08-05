"""Integrations CLI command handlers."""

from __future__ import annotations

import json

from keprix.integrations.google_workspace.bridge import GoogleWorkspaceBridge, GoogleWorkspaceError


def cmd_integrations(args) -> int:
    if args.integrations_command != "google-workspace":
        print(json.dumps({"error": "unknown integrations command"}))
        return 2
    bridge = GoogleWorkspaceBridge()
    try:
        if args.google_workspace_command == "status":
            print(json.dumps(bridge.status(), indent=2))
            return 0
        if args.google_workspace_command == "login":
            print(json.dumps(bridge.auth_url(redirect_uri=args.redirect_uri), indent=2))
            return 0
        if args.google_workspace_command == "callback":
            payload = {
                "code": args.code,
                "access_token": args.access_token,
                "account_email": args.account_email,
            }
            print(json.dumps(bridge.exchange_callback({key: value for key, value in payload.items() if value}), indent=2))
            return 0
        if args.google_workspace_command == "logout":
            print(json.dumps(bridge.logout(), indent=2))
            return 0
    except GoogleWorkspaceError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1
    print(json.dumps({"error": "unknown google-workspace command"}))
    return 2
