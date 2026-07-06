#!/usr/bin/env python3
"""Post-login first-run onboarding for keprix."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    state_path = Path.home() / ".keprix" / "first_run.json"
    if state_path.exists():
        data = json.loads(state_path.read_text(encoding="utf-8"))
        if data.get("completed"):
            print("First-run onboarding already completed.")
            return 0

    print("keprix first-run onboarding")
    print("1. Configure an LLM provider in Settings > Providers")
    print("2. Open http://localhost:3000/chat and send a test message")
    print("3. Run `keprix health` to verify services")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"completed": True, "version": 1}), encoding="utf-8")
    print("Done. Welcome to keprix.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
