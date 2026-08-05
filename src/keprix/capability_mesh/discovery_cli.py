"""CLI: python3 -m keprix.capability_mesh.discovery --write"""

from __future__ import annotations

import argparse
import sys

from keprix.capability_mesh.discovery import render_discovery_markdown, write_discovery


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--path", default="")
    args = parser.parse_args(argv)
    if args.write:
        from pathlib import Path

        path = write_discovery(Path(args.path) if args.path else None)
        print(f"wrote {path}")
        return 0
    print(render_discovery_markdown())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
