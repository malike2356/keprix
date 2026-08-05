"""Forensic chain-of-custody verification."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from keprix.forensics.snapshot import _snapshots_dir, load_snapshot


def verify_chain() -> dict[str, Any]:
    chain_path = _snapshots_dir().parent / "chain.jsonl"
    if not chain_path.exists():
        return {"ok": True, "entries": 0, "message": "no chain recorded yet"}

    lines = [line.strip() for line in chain_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    prev_hash = "genesis"
    verified = 0
    errors: list[str] = []

    for index, line in enumerate(lines, start=1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"line {index}: invalid json")
            continue
        snapshot_id = str(entry.get("snapshot_id") or "")
        if entry.get("prev_hash") != prev_hash:
            errors.append(f"{snapshot_id}: prev_hash mismatch")
        try:
            payload = load_snapshot(snapshot_id)
        except FileNotFoundError:
            errors.append(f"{snapshot_id}: snapshot file missing")
            prev_hash = str(entry.get("hash") or prev_hash)
            continue
        body = {key: value for key, value in payload.items() if key not in {"hash", "prev_hash"}}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        expected = hashlib.sha256(f"{prev_hash}:{canonical}".encode("utf-8")).hexdigest()
        if expected != entry.get("hash"):
            errors.append(f"{snapshot_id}: hash mismatch")
        prev_hash = str(entry.get("hash") or prev_hash)
        verified += 1

    return {
        "ok": not errors,
        "entries": len(lines),
        "verified": verified,
        "errors": errors,
    }
