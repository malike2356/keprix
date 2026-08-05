"""python -m keprix.capability_mesh"""

from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "audit":
        from keprix.capability_mesh.audit import main as audit_main

        return audit_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "discovery":
        from keprix.capability_mesh import discovery as discovery_mod
        import argparse
        from pathlib import Path

        parser = argparse.ArgumentParser()
        parser.add_argument("--write", action="store_true")
        parser.add_argument("--path", default="")
        args = parser.parse_args(sys.argv[2:])
        if args.write:
            path = discovery_mod.write_discovery(Path(args.path) if args.path else None)
            print(f"wrote {path}")
            return 0
        print(discovery_mod.render_discovery_markdown())
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "dod":
        from keprix.capability_mesh.dod import assert_dod
        import json

        print(json.dumps(assert_dod(), indent=2))
        return 0 if assert_dod()["ok"] else 1

    print("Usage: python -m keprix.capability_mesh audit [--write] [--json]")
    print("       python -m keprix.capability_mesh dod")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
