#!/usr/bin/env python3
"""Interactive Keprix setup wizard (Prompt 33)."""

from __future__ import annotations

import os
import sys


def main() -> int:
    from keprix.installer.wizard import run_wizard

    create_identity = None
    if os.environ.get("KEPRIX_SKIP_IDENTITY", "").lower() not in {"1", "true", "yes"}:
        from keprix.keys.developer_identity import create_developer_identity

        create_identity = create_developer_identity

    result = run_wizard(create_developer_identity=create_identity)
    print(f"Wrote {result.env_path}")
    if result.developer_identity_created:
        print("Developer identity created at ~/.keprix/identity/dev.json")
    print("")
    print("Admin password (save this now):")
    print(result.admin_password)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
