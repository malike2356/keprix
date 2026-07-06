"""CLI entry for `keprix tui`."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys


def run_tui(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[2:] if argv is None else argv)

    parser = argparse.ArgumentParser(
        prog="keprix tui",
        description="Launch the Keprix terminal chat UI",
        epilog=(
            "Mouse is off by default so you can select and copy text in the terminal.\n"
            "  PYTHONPATH=src python3 -m keprix tui\n"
            "  PYTHONPATH=src python3 -m keprix tui --mouse   # click sessions in the sidebar\n"
            "Keyboard: Ctrl+S sessions | Ctrl+Shift+L copy last reply | Ctrl+Shift+C copy all"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--session", dest="session_id", default=None, help="Resume a conversation session")
    parser.add_argument("--model", default=None, help="Default model id")
    parser.add_argument("--url", default=None, help="Keprix API base URL")
    parser.add_argument("--token", default=None, help="Bearer token when auth is enabled")
    parser.add_argument(
        "--mouse",
        action="store_true",
        help="Enable mouse capture for clicking sessions (off by default so terminal copy works)",
    )
    parser.add_argument(
        "--no-mouse",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    use_mouse = args.mouse and not args.no_mouse

    try:
        from keprix.tui.app import KeprixTuiApp
        from keprix.tui.client import KeprixClient
    except ImportError as exc:
        print("Textual is required for the TUI. Install with: pip install 'keprix[tui]'")
        print(f"Detail: {exc}")
        return 1

    client = KeprixClient(base_url=args.url, token=args.token, model=args.model)
    app = KeprixTuiApp(client=client, session_id=args.session_id, model=args.model)
    asyncio.run(app.run_async(mouse=use_mouse))
    return 0


if __name__ == "__main__":
    sys.exit(run_tui(sys.argv[1:]))
