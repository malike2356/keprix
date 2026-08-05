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
            "Mouse is off by default so you can shift+drag to select text in the terminal.\n"
            "  keprix tui\n"
            "  keprix tui --mouse\n"
            "      Enable mouse capture: click sessions and drag-select transcript text.\n"
            "Keyboard: Ctrl+Shift+T focus transcript | Ctrl+Shift+C copy selection or all\n"
            "          Ctrl+Shift+L copy last reply | Ctrl+S sessions"
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
        help="Enable mouse capture for sidebar clicks and in-TUI transcript selection",
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
        print("Textual is required for the TUI. Install with: pipx install 'keprix[tui]'")
        print(f"Detail: {exc}")
        return 1

    client = KeprixClient(base_url=args.url, token=args.token, model=args.model)
    app = KeprixTuiApp(
        client=client,
        session_id=args.session_id,
        model=args.model,
        mouse_enabled=use_mouse,
    )
    asyncio.run(app.run_async(mouse=use_mouse))
    return 0


if __name__ == "__main__":
    sys.exit(run_tui(sys.argv[1:]))
