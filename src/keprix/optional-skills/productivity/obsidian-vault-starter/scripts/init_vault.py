#!/usr/bin/env python3
"""Initialize an Obsidian starter vault from the bundled pack."""

from __future__ import annotations

import argparse
import json

from keprix.vault.vault_init_service import init_vault


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--pack", default="obsidian-starter")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(json.dumps(init_vault(pack=args.pack, path=args.path, overwrite=args.overwrite), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
