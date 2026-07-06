"""App Foundation SDK CLI commands."""

from __future__ import annotations

import json
import sys

from keprix.sdk.domain_context import parse_message
from keprix.sdk.schemas import DomainSchema
from keprix.sdk.store import SdkStore, get_sdk_store


def _store() -> SdkStore:
    return get_sdk_store()


def cmd_sdk_list(_args) -> int:
    apps = _store().list_apps()
    if not apps:
        print("No registered SDK apps.")
        return 0
    for app in apps:
        entities = len(app.get("domain_schema", {}).get("entities", []))
        print(f"{app['id']}  {app['name']}  v{app['version']}  entities={entities}")
    return 0


def cmd_sdk_show(args) -> int:
    app = _store().get_app(args.app_id)
    if not app:
        print(f"App not found: {args.app_id}", file=sys.stderr)
        return 1
    print(json.dumps(app, indent=2))
    return 0


def cmd_sdk_unregister(args) -> int:
    if not _store().unregister_app(args.app_id):
        print(f"App not found: {args.app_id}", file=sys.stderr)
        return 1
    print(f"Unregistered {args.app_id}")
    return 0


def cmd_sdk_test(args) -> int:
    store = _store()
    app = store.get_app(args.app_id)
    if not app:
        print(f"App not found: {args.app_id}", file=sys.stderr)
        return 1
    domain = DomainSchema.model_validate(app["domain_schema"])
    print(f"Testing app {app['name']} ({args.app_id}). Type NL commands; empty line to quit.")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            break
        plan = parse_message(domain, line)
        print(json.dumps(plan.model_dump(), indent=2))
    return 0
