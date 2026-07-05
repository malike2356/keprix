"""Entry point: python -m keprix  or  keprix CLI command."""

from __future__ import annotations

import sys


def main() -> None:
    try:
        from keprix.api.cli import cli_main
    except ImportError:
        print("keprix CLI is not installed. Run: pip install -e '.[dev]' from the repo root.")
        raise SystemExit(1) from None
    cli_main(sys.argv[1:])


if __name__ == "__main__":
    main()
