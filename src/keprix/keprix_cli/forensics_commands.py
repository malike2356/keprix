"""CLI handlers for ``keprix forensics``."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.forensics.chain import verify_chain
from keprix.forensics.snapshot import analyze_snapshot, capture_snapshot, export_snapshot, list_snapshots


def cmd_forensics(args) -> int:
    command = args.forensics_command
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

    if command == "list":
        rows = list_snapshots()
        print(json.dumps(rows, indent=2))
        return 0

    if command == "analyze":
        payload = analyze_snapshot(args.snapshot)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Snapshot {args.snapshot}: {payload.get('signal_count')} signals")
            for item in payload.get("recommendations") or []:
                print(f"  - {item}")
        return 0

    if command == "export":
        output = Path(args.output) if args.output else None
        path = export_snapshot(args.snapshot, output=output)
        print(json.dumps({"exported_to": str(path)}, indent=2))
        return 0

    if command == "chain-verify":
        payload = verify_chain()
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("ok") else 1

    print(json.dumps({"error": f"unknown forensics command: {command}"}))
    return 2
