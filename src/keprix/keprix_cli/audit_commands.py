"""CLI handlers for ``keprix audit``."""

from __future__ import annotations

import json

from keprix.forensics.chain import verify_chain


def cmd_audit(args) -> int:
    if args.audit_command == "verify":
        payload = verify_chain()
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("ok") else 1
    print(json.dumps({"error": f"unknown audit command: {args.audit_command}"}))
    return 2
