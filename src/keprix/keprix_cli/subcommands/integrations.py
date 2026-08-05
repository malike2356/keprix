"""Integrations CLI parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_integrations_parser(subparsers: _SubParsersAction, *, cmd_integrations: Callable) -> None:
    parser = subparsers.add_parser("integrations", help="Manage optional integrations")
    sub = parser.add_subparsers(dest="integrations_command", required=True)

    gws = sub.add_parser("google-workspace", help="Google Workspace connector")
    gws_sub = gws.add_subparsers(dest="google_workspace_command", required=True)
    gws_sub.add_parser("status", help="Show connector status").set_defaults(func=cmd_integrations)
    login = gws_sub.add_parser("login", help="Print OAuth URL for desktop flow")
    login.add_argument("--redirect-uri", default="http://localhost:8751/api/integrations/google-workspace/oauth/callback")
    login.set_defaults(func=cmd_integrations)
    callback = gws_sub.add_parser("callback", help="Store callback token metadata")
    callback.add_argument("--code")
    callback.add_argument("--access-token")
    callback.add_argument("--account-email")
    callback.set_defaults(func=cmd_integrations)
    gws_sub.add_parser("logout", help="Remove local token metadata").set_defaults(func=cmd_integrations)
