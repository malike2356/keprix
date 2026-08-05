#!/usr/bin/env python3
"""
Laud's Gmail Inbox Reader
=========================
Reads Gmail inbox via Google Workspace OAuth. Uses the Hermes Google
Workspace skill backend. Requires prior OAuth setup (google_token.json).

Usage:
  python inbox.py                          # Recent unread (last 20)
  python inbox.py --all                    # All unread
  python inbox.py --from sender@x.com      # From specific sender
  python inbox.py --search "subject:Invoice"
  python inbox.py --since 2d               # Last 2 days
  python inbox.py --id MESSAGE_ID          # Read full message
  python inbox.py --watch                  # Poll every 60s, alert on matches
  python inbox.py --contacts               # Flag emails from known contacts

Output: JSON to stdout. Pipe through jq for formatting.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

GAPI = str(
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / ".hermes/agent-sync/skills/productivity/google-workspace/scripts/google_api.py"
)

# Fallback if relative resolution fails (different machine layouts)
if not Path(GAPI).exists():
    GAPI = str(
        Path.home()
        / ".hermes/agent-sync/skills/productivity/google-workspace/scripts/google_api.py"
    )

KNOWN_CONTACTS = [
    "sam.simon@tallyaccountants.co.uk",
    "tallyaccountants.co.uk",
    "frank@dorsetbusinessangels.co.uk",
    "dorsetbusinessangels",
    "laudpaulgablah@gmail.com",
    "lordsesame@gmail.com",
    "salim",
]


def run_gapi(*args):
    """Run a google_api.py command and return parsed JSON."""
    result = subprocess.run(
        ["python3", GAPI, *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"ERROR: {result.stderr.strip()}", file=sys.stderr)
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout


def is_known(sender: str) -> bool:
    """Check if sender matches any known contact."""
    sender_lower = sender.lower()
    return any(c.lower() in sender_lower for c in KNOWN_CONTACTS)


def format_email(msg: dict) -> dict:
    """Format a Gmail message for display."""
    return {
        "id": msg.get("id", ""),
        "from": msg.get("from", ""),
        "subject": msg.get("subject", ""),
        "date": msg.get("date", ""),
        "snippet": (msg.get("snippet", "") or "")[:200],
        "known": is_known(msg.get("from", "")),
    }


def search_unread(query="is:unread", max_results=20):
    """Search unread emails."""
    args = ["gmail", "search", query, "--max", str(max_results)]
    return run_gapi(*args) or []


def get_message(msg_id: str):
    """Get full message body."""
    return run_gapi("gmail", "get", msg_id)


def watch(interval=60):
    """Poll for new emails and print when found."""
    seen_ids = set()
    print(f"Watching inbox every {interval}s...", file=sys.stderr)

    while True:
        try:
            messages = search_unread(max_results=10)
            for msg in messages:
                mid = msg.get("id", "")
                if mid not in seen_ids:
                    seen_ids.add(mid)
                    formatted = format_email(msg)
                    print(json.dumps(formatted, ensure_ascii=False))
                    sys.stdout.flush()
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped.", file=sys.stderr)
            break
        except Exception as e:
            print(f"Watch error: {e}", file=sys.stderr)
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Laud's Gmail Inbox Reader")
    parser.add_argument("--all", action="store_true", help="Show all unread (no limit)")
    parser.add_argument("--from", dest="sender", help="Filter by sender")
    parser.add_argument("--search", help="Gmail search query")
    parser.add_argument("--since", help="Time filter (e.g., 1d, 2d, 7d)")
    parser.add_argument("--id", dest="msg_id", help="Read full message by ID")
    parser.add_argument("--watch", action="store_true", help="Poll for new emails")
    parser.add_argument("--contacts", action="store_true", help="Only emails from known contacts")
    parser.add_argument("--interval", type=int, default=60, help="Watch interval in seconds")
    args = parser.parse_args()

    if args.msg_id:
        msg = get_message(args.msg_id)
        if msg:
            print(json.dumps(msg, indent=2, ensure_ascii=False))
        return

    if args.watch:
        watch(interval=args.interval)
        return

    # Build query
    query = "is:unread"
    if args.sender:
        query += f" from:{args.sender}"
    if args.since:
        query += f" newer_than:{args.since}"
    if args.search:
        query = args.search

    limit = 500 if args.all else 20
    messages = search_unread(query=query, max_results=limit)

    if not isinstance(messages, list):
        print("[]")
        return

    output = []
    for msg in messages:
        formatted = format_email(msg)
        if args.contacts and not formatted["known"]:
            continue
        output.append(formatted)

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
