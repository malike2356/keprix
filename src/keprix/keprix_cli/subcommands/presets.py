"""``keprix presets`` CLI for capability packs."""

from __future__ import annotations

import json
import sys
from typing import Callable


def build_presets_parser(subparsers, *, cmd_presets: Callable) -> None:
    parser = subparsers.add_parser(
        "presets",
        help="List, show, apply, or diff capability presets (coding/crm/sidecar)",
        description=(
            "Declarative capability packs that mount plugins/skills/seams "
            "via reversible lifecycle. Soft Wall cannot be disabled by a pack."
        ),
    )
    parser.set_defaults(func=cmd_presets)
    sub = parser.add_subparsers(dest="presets_action")

    sub.add_parser("list", help="List available capability presets")
    show_p = sub.add_parser("show", help="Show a preset definition")
    show_p.add_argument("name", help="Preset name (coding, crm, sidecar, …)")
    apply_p = sub.add_parser("apply", help="Apply a preset (hot mount/unmount)")
    apply_p.add_argument("name", help="Preset name to apply")
    apply_p.add_argument(
        "--skip-unknown-plugins",
        action="store_true",
        help="Skip unknown plugin ids instead of failing closed",
    )
    diff_p = sub.add_parser("diff", help="Diff two presets (or active → target)")
    diff_p.add_argument("to_name", help="Target preset name")
    diff_p.add_argument(
        "--from",
        dest="from_name",
        default=None,
        help="Source preset (default: currently active)",
    )
    active_p = sub.add_parser("active", help="Show the currently applied preset")
    del active_p  # registered for side effect


def cmd_presets(args) -> int:
    from keprix.capability_presets import (
        PresetValidationError,
        apply_preset,
        diff_presets,
        get_active_state,
        list_available_presets,
        show_preset,
    )

    action = getattr(args, "presets_action", None) or "list"
    try:
        if action == "list":
            for preset in list_available_presets():
                print(f"{preset['name']}\t{preset.get('description', '').splitlines()[0][:80]}")
            return 0
        if action == "show":
            print(json.dumps(show_preset(args.name), indent=2))
            return 0
        if action == "active":
            print(json.dumps(get_active_state(), indent=2))
            return 0
        if action == "diff":
            state = get_active_state()
            from_name = args.from_name or state.get("active")
            print(json.dumps(diff_presets(from_name, args.to_name), indent=2))
            return 0
        if action == "apply":
            strict = False if getattr(args, "skip_unknown_plugins", False) else None
            result = apply_preset(args.name, who="cli", strict_plugins=strict)
            print(json.dumps(result, indent=2))
            return 0 if result.get("ok") else 1
        print(f"Unknown presets action: {action}", file=sys.stderr)
        return 2
    except PresetValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
