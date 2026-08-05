"""CLI handlers for ``keprix policy`` (Prompt 297)."""

from __future__ import annotations

import json


def cmd_policy(args) -> int:
    from keprix.security.operator_policy import (
        get_operator_policy,
        profile_knob_diff,
        set_operator_policy,
    )

    product = (getattr(args, "product", None) or "").strip() or None
    workspace = (getattr(args, "workspace", None) or "default").strip() or "default"
    command = getattr(args, "policy_command", None)

    if command == "show":
        policy = get_operator_policy(product_id=product, workspace_id=workspace)
        payload = {
            **policy.to_dict(),
            "knob_matrix": profile_knob_diff(),
        }
        print(json.dumps(payload, indent=2))
        return 0

    if command == "set":
        profile = getattr(args, "profile", None)
        if not profile:
            print(json.dumps({"error": "missing --profile"}))
            return 2
        policy = set_operator_policy(
            profile,
            product_id=product,
            workspace_id=workspace,
            updated_by="cli",
        )
        print(json.dumps({"ok": True, **policy.to_dict()}, indent=2))
        return 0

    print(json.dumps({"error": f"unknown policy command: {command}"}))
    return 2
