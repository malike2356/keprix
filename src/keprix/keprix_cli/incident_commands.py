"""CLI handlers for ``keprix incident``."""

from __future__ import annotations

import json

from keprix.forensics.snapshot import capture_snapshot
from keprix.incident.response import (
    declare_incident,
    lockdown_product,
    render_post_mortem,
    rotate_credentials,
    seal_vault,
)
from keprix.incident.severity import IncidentLevel
from keprix.incident.store import list_incidents


def cmd_incident(args) -> int:
    command = args.incident_command
    if command == "declare":
        payload = declare_incident(
            level=IncidentLevel.from_label(args.level),
            reason=args.reason,
            product_id=args.product,
            session_id=args.session,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Declared {payload['severity']} incident {payload['incident']['id']}")
        return 0

    if command == "snapshot":
        payload = capture_snapshot(
            session_id=args.session,
            product_id=args.product,
            reason=args.reason,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Captured snapshot {payload.get('id')}")
        return 0

    if command == "rotate-creds":
        payload = rotate_credentials(product_id=args.product)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Rotation signals queued for product={args.product}")
        return 0

    if command == "seal-vault":
        payload = seal_vault(reason="operator_command")
        print(json.dumps(payload, indent=2))
        return 0

    if command == "lockdown":
        payload = lockdown_product(args.product, reason=args.reason)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Lockdown applied to {args.product}: {', '.join(payload.get('actions') or [])}")
        return 0

    if command == "post-mortem":
        print(render_post_mortem(args.incident_id))
        return 0

    if command == "list":
        rows = list_incidents()
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                print(f"- {row.get('id')}: {row.get('level')} {row.get('reason')}")
        return 0

    print(json.dumps({"error": f"unknown incident command: {command}"}))
    return 2
