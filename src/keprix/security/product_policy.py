"""Per-product Scout security policies."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix_cli.config import get_keprix_home

logger = logging.getLogger(__name__)


def _policy_path() -> Path:
    return get_keprix_home() / "scout" / "product_policies.json"


def _load_all() -> dict[str, Any]:
    path = _policy_path()
    if not path.exists():
        return {"policies": {}, "history": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"policies": {}, "history": []}


def _save_all(data: dict[str, Any]) -> None:
    path = _policy_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_policies() -> dict[str, dict[str, Any]]:
    return dict(_load_all().get("policies") or {})


def get_policy(product_id: str) -> dict[str, Any] | None:
    row = list_policies().get(product_id)
    return dict(row) if row else None


def policy_history(product_id: str | None = None, *, limit: int = 20) -> list[dict[str, Any]]:
    history = list(_load_all().get("history") or [])
    if product_id:
        history = [row for row in history if row.get("product_id") == product_id]
    return history[-limit:]


def apply_product_policy(product_id: str, policy: dict[str, Any], *, updated_by: str = "scout") -> dict[str, Any]:
    """Persist and enforce a per-product policy."""
    data = _load_all()
    policies = dict(data.get("policies") or {})
    record = {
        "product": product_id,
        "security_profile": policy.get("security_profile") or policy.get("security_policy") or "standard",
        "version": int((policies.get(product_id) or {}).get("version") or 0) + 1,
        "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "updated_by": updated_by,
        "sandbox": policy.get("sandbox") or {},
        "egress": policy.get("egress") or {},
        "tools": policy.get("tools") or {},
        "governance": policy.get("governance") or {},
        "credentials": policy.get("credentials") or {},
        "audit": policy.get("audit") or {},
    }
    policies[product_id] = record
    history = list(data.get("history") or [])
    history.append(
        {
            "product_id": product_id,
            "version": record["version"],
            "updated_at": record["last_updated"],
            "updated_by": updated_by,
        }
    )
    data["policies"] = policies
    data["history"] = history[-200:]
    _save_all(data)
    _enforce(product_id, record)
    return record


def _enforce(product_id: str, policy: dict[str, Any]) -> None:
    tools = policy.get("tools") or {}
    for tool_name in tools.get("quarantined_tools") or []:
        name = str(tool_name).strip()
        if name:
            try:
                from keprix.governance.policy_receiver import get_policy_registry
                from keprix.security.scout_control import quarantine_tool

                quarantine_tool(name)
                get_policy_registry().apply("tool_block", {"tool_name": name, "product_id": product_id})
            except Exception:
                logger.debug("tool policy apply failed for %s", name, exc_info=True)

    rate_limits = tools.get("rate_limits") or {}
    default_limit = rate_limits.get("default") or {}
    if default_limit.get("per_minute"):
        try:
            from keprix.governance.policy_receiver import get_policy_registry

            get_policy_registry().apply(
                "rate_limit",
                {"calls_per_minute": int(default_limit["per_minute"]), "product_id": product_id},
            )
        except Exception:
            pass

    egress = policy.get("egress") or {}
    allowed = egress.get("allowed_domains") or egress.get("allowed_hosts") or []
    if allowed:
        hosts = set()
        for entry in allowed:
            host = str(entry).split(":", 1)[0].strip()
            if host:
                hosts.add(host)
        try:
            from keprix.security.egress_policy import get_egress_policy

            get_egress_policy().load_product(product_id, allowed_hosts=hosts, default_deny=True)
        except Exception:
            logger.debug("egress policy apply failed for %s", product_id, exc_info=True)

    sandbox = policy.get("sandbox") or {}
    if str(sandbox.get("mode") or "").lower() == "session_only":
        try:
            from keprix.security.scout_control import set_egress_force_blocked

            set_egress_force_blocked(True)
        except Exception:
            pass
