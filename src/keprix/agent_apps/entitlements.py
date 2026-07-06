"""Agent Apps entitlements and usage limits."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from keprix.agent_apps.registry import get_agent_app_registry
from keprix.agent_apps.run_store import _connect, init_run_store
from keprix.billing.feature_gates.enforcer import check_feature

_CONFIG_CACHE: dict[str, Any] | None = None

ENTITLEMENT_MESSAGES: dict[str, str] = {
    "agent_apps.enabled": "Agent Apps are disabled on this instance.",
    "agent_apps.marketplace": "The agent app marketplace is not available on your plan.",
    "agent_apps.pro_templates": "Pro marketplace templates require a paid plan.",
    "agent_apps.scheduled": "Scheduled agent app runs are available on Pro and above.",
    "agent_apps.webhooks": "Agent app webhooks are available on Team and above.",
    "agent_apps.publish": "Publishing agent app bundles requires Team or Enterprise.",
    "agent_apps.max_installed": "You have reached the install limit for your plan.",
    "agent_apps.max_runs_per_month": "You have used all agent app runs for this month.",
    "agent_apps.max_scheduled": "You have reached the scheduled agent app limit for your plan.",
}


def _config_path() -> Path:
    env_path = os.environ.get("KEPRIX_AGENT_APPS_CONFIG", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    return Path(__file__).resolve().parents[3] / "config" / "agent_apps.yaml"


def load_agent_apps_config() -> dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    path = _config_path()
    if not path.exists():
        _CONFIG_CACHE = {"features": {}, "limits": {}, "retention": {"run_history_days": 30}}
        return _CONFIG_CACHE
    _CONFIG_CACHE = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _CONFIG_CACHE


def reset_agent_apps_config_cache() -> None:
    global _CONFIG_CACHE
    _CONFIG_CACHE = None


def _product_agent_apps_enabled() -> bool:
    try:
        from keprix.governance.policy_receiver import get_policy_registry

        if not get_policy_registry().feature_enabled("agent_apps.enabled", default=True):
            return False
    except Exception:
        pass
    try:
        from keprix.products.loader import get_product_feature_flags

        flags = get_product_feature_flags()
        if "agent_apps.enabled" in flags:
            return bool(flags["agent_apps.enabled"])
    except Exception:
        pass
    env = os.environ.get("KEPRIX_AGENT_APPS_ENABLED", "").strip().lower()
    if env in {"0", "false", "no", "off"}:
        return False
    if env in {"1", "true", "yes", "on"}:
        return True
    return True


def _plan_limit(plan: str, key: str, default: int) -> int | None:
    cfg = load_agent_apps_config()
    limits = cfg.get("limits") or {}
    bucket = limits.get(key) or {}
    if isinstance(bucket, dict):
        raw = bucket.get(plan, bucket.get("community", default))
        if isinstance(raw, str) and raw.lower() == "unlimited":
            return None
        value = int(raw)
        if value >= 999999:
            return None
        return value
    return default


async def resolve_user_plan(user_id: str) -> str:
    del user_id
    override = os.environ.get("KEPRIX_BILLING_PLAN_OVERRIDE", "").strip()
    if override:
        return override
    try:
        from keprix.billing.config_loader import billing_enabled, load_billing_config
        from keprix.billing.store import get_billing_store

        if not billing_enabled():
            return "community"
        sub = await get_billing_store().get_subscription(user_id)
        if sub and sub.get("plan_id"):
            return str(sub["plan_id"])
        cfg = load_billing_config()
        community = cfg.community_plan() if cfg else None
        if community:
            return community.id
    except Exception:
        pass
    return "community"


async def _feature_enabled(user_id: str, feature: str, *, config_key: str) -> bool:
    if not _product_agent_apps_enabled():
        return False
    cfg = load_agent_apps_config()
    default = bool((cfg.get("features") or {}).get(config_key, False))
    if default:
        return True
    return await check_feature(user_id, feature, min_value=True)


async def agent_apps_enabled(user_id: str) -> bool:
    if not _product_agent_apps_enabled():
        return False
    cfg = load_agent_apps_config()
    default = bool((cfg.get("features") or {}).get("agent_apps.enabled", True))
    if not default:
        return False
    return await check_feature(user_id, "agent_apps.enabled", min_value=True)


async def marketplace_enabled(user_id: str) -> bool:
    return await _feature_enabled(user_id, "agent_apps.marketplace", config_key="agent_apps.marketplace")


async def scheduled_enabled(user_id: str) -> bool:
    return await _feature_enabled(user_id, "agent_apps.scheduled", config_key="agent_apps.scheduled")


async def webhooks_enabled(user_id: str) -> bool:
    return await _feature_enabled(user_id, "agent_apps.webhooks", config_key="agent_apps.webhooks")


async def publish_enabled(user_id: str) -> bool:
    return await _feature_enabled(user_id, "agent_apps.publish", config_key="agent_apps.publish")


async def pro_templates_enabled(user_id: str) -> bool:
    return await _feature_enabled(user_id, "agent_apps.pro_templates", config_key="agent_apps.pro_templates")


def _count_billable_runs_this_month() -> int:
    init_run_store()
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM runs
            WHERE started_at >= ? AND status = 'success'
            """,
            (month_start.isoformat(),),
        ).fetchone()
    return int(row["count"]) if row else 0


def _count_enabled_schedules() -> int:
    from keprix.agent_apps.automation import count_enabled_schedules

    return count_enabled_schedules()


def entitlement_message(code: str, usage: dict[str, Any] | None = None) -> str:
    usage = usage or {}
    if code == "agent_apps.max_installed":
        return (
            f"You have installed {usage.get('installed_count', 0)} of "
            f"{usage.get('installed_limit', '?')} agent apps."
        )
    if code == "agent_apps.max_runs_per_month":
        return (
            f"You have used {usage.get('runs_this_month', 0)} of "
            f"{usage.get('runs_limit', '?')} agent app runs this month."
        )
    if code == "agent_apps.max_scheduled":
        return (
            f"You have {usage.get('scheduled_count', 0)} of "
            f"{usage.get('scheduled_limit', '?')} scheduled agent apps."
        )
    return ENTITLEMENT_MESSAGES.get(code, code)


def entitlement_http_detail(code: str, usage: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "detail": code,
        "message": entitlement_message(code, usage),
        "upgrade_url": "/pricing",
        "usage": usage or {},
    }


async def usage_summary(user_id: str, *, plan: str | None = None) -> dict[str, Any]:
    plan_name = plan or await resolve_user_plan(user_id)
    runs_limit = _plan_limit(plan_name, "agent_apps.max_runs_per_month", 50)
    installed_limit = _plan_limit(plan_name, "agent_apps.max_installed", 3)
    scheduled_limit = _plan_limit(plan_name, "agent_apps.max_scheduled", 5)
    runs_this_month = _count_billable_runs_this_month()
    installed_count = get_agent_app_registry().installed_count()
    scheduled_count = _count_enabled_schedules()
    return {
        "runs_this_month": runs_this_month,
        "runs_limit": runs_limit,
        "installed_count": installed_count,
        "installed_limit": installed_limit,
        "scheduled_count": scheduled_count,
        "scheduled_limit": scheduled_limit,
        "plan": plan_name,
        "features": {
            "marketplace": await marketplace_enabled(user_id),
            "pro_templates": await pro_templates_enabled(user_id),
            "scheduled": await scheduled_enabled(user_id),
            "webhooks": await webhooks_enabled(user_id),
            "publish": await publish_enabled(user_id),
        },
        "near_run_limit": runs_limit is not None and runs_limit > 0 and runs_this_month >= int(runs_limit * 0.8),
    }


async def assert_can_install(user_id: str, *, plan: str | None = None) -> None:
    if not await agent_apps_enabled(user_id):
        raise PermissionError("agent_apps.enabled")
    plan_name = plan or await resolve_user_plan(user_id)
    usage = await usage_summary(user_id, plan=plan_name)
    limit = usage["installed_limit"]
    if limit is not None and usage["installed_count"] >= limit:
        raise PermissionError("agent_apps.max_installed")


async def assert_can_run(user_id: str, *, plan: str | None = None) -> None:
    if not await agent_apps_enabled(user_id):
        raise PermissionError("agent_apps.enabled")
    plan_name = plan or await resolve_user_plan(user_id)
    usage = await usage_summary(user_id, plan=plan_name)
    limit = usage["runs_limit"]
    if limit is not None and usage["runs_this_month"] >= limit:
        raise PermissionError("agent_apps.max_runs_per_month")


async def assert_can_schedule(user_id: str, app_name: str, *, plan: str | None = None) -> None:
    if not await agent_apps_enabled(user_id):
        raise PermissionError("agent_apps.enabled")
    if not await scheduled_enabled(user_id):
        raise PermissionError("agent_apps.scheduled")
    from keprix.agent_apps.automation import get_schedule

    plan_name = plan or await resolve_user_plan(user_id)
    usage = await usage_summary(user_id, plan=plan_name)
    limit = usage["scheduled_limit"]
    if limit is None:
        return
    existing = get_schedule(app_name)
    if existing and existing.get("enabled"):
        return
    if usage["scheduled_count"] >= limit:
        raise PermissionError("agent_apps.max_scheduled")


async def assert_can_webhook(user_id: str) -> None:
    if not await agent_apps_enabled(user_id):
        raise PermissionError("agent_apps.enabled")
    if not await webhooks_enabled(user_id):
        raise PermissionError("agent_apps.webhooks")


async def assert_can_publish(user_id: str) -> None:
    if not await agent_apps_enabled(user_id):
        raise PermissionError("agent_apps.enabled")
    if not await publish_enabled(user_id):
        raise PermissionError("agent_apps.publish")


async def assert_can_install_catalog_template(user_id: str, template_id: str) -> None:
    from keprix.agent_apps.catalog import get_catalog_template

    await assert_can_install(user_id)
    if not await marketplace_enabled(user_id):
        raise PermissionError("agent_apps.marketplace")
    item = get_catalog_template(template_id)
    if item is None:
        raise FileNotFoundError(f"Catalog template not found: {template_id}")
    if item.get("tier") == "pro" and not await pro_templates_enabled(user_id):
        raise PermissionError("agent_apps.pro_templates")
