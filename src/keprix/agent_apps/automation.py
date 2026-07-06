"""Agent app scheduling, webhooks, and cron integration."""

from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from keprix.agent_apps.registry import get_agent_app_registry
from keprix.agent_apps.web_runner import run_api, run_scheduled

DEFAULT_WEBHOOK_RATE_LIMIT = 60


def _automation_root() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "agent_apps"
    except Exception:
        root = Path.home() / ".keprix" / "agent_apps"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _schedules_path() -> Path:
    return _automation_root() / "schedules.json"


def _webhooks_path() -> Path:
    return _automation_root() / "webhooks.json"


def webhook_rate_limit() -> int:
    raw = os.environ.get("KEPRIX_AGENT_APP_WEBHOOK_RATE_LIMIT", "").strip()
    if raw.isdigit():
        return int(raw)
    return DEFAULT_WEBHOOK_RATE_LIMIT


def webhook_ip_allowed(client_ip: str | None) -> bool:
    allowlist = os.environ.get("KEPRIX_AGENT_APP_WEBHOOK_IP_ALLOWLIST", "").strip()
    if not allowlist:
        return True
    if not client_ip:
        return False
    allowed = {item.strip() for item in allowlist.split(",") if item.strip()}
    return client_ip in allowed


def public_base_url(request_base: str | None = None) -> str:
    explicit = os.environ.get("KEPRIX_PUBLIC_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    if request_base:
        return request_base.rstrip("/")
    return "http://localhost:3333"


def _cron_jobs_module():
    root = Path(__file__).resolve().parents[1]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from cron import jobs as cron_jobs
    from keprix_constants import get_keprix_home

    home = get_keprix_home().resolve()
    cron_jobs.KEPRIX_DIR = home
    cron_jobs.CRON_DIR = home / "cron"
    cron_jobs.JOBS_FILE = cron_jobs.CRON_DIR / "jobs.json"
    cron_jobs.OUTPUT_DIR = cron_jobs.CRON_DIR / "output"
    return cron_jobs


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_schedules() -> dict[str, Any]:
    data = _load_json(_schedules_path())
    return dict(data.get("apps") or {})


def count_enabled_schedules() -> int:
    return sum(1 for row in _load_schedules().values() if row.get("enabled"))


def _save_schedules(apps: dict[str, Any]) -> None:
    _save_json(_schedules_path(), {"apps": apps, "updated_at": datetime.now(timezone.utc).isoformat()})


def _load_webhook_store() -> dict[str, Any]:
    data = _load_json(_webhooks_path())
    if "apps" not in data:
        data["apps"] = {}
    if "tokens" not in data:
        data["tokens"] = {}
    return data


def _save_webhook_store(store: dict[str, Any]) -> None:
    _save_json(_webhooks_path(), store)


def get_schedule(app_name: str) -> dict[str, Any] | None:
    row = _load_schedules().get(app_name)
    if not row:
        return None
    return dict(row)


def upsert_schedule(
    app_name: str,
    *,
    cron: str,
    timezone_name: str,
    inputs: dict[str, Any],
    enabled: bool,
) -> dict[str, Any]:
    registry = get_agent_app_registry()
    app_row = registry.get(app_name)
    if app_row is None:
        raise ValueError(f"Agent app not installed: {app_name}")
    display_name = app_row.get("display_name") or app_name
    cron_jobs = _cron_jobs_module()
    schedules = _load_schedules()
    existing = schedules.get(app_name) or {}
    payload = {
        "app_name": app_name,
        "inputs": inputs,
        "runner": "scheduled",
        "timezone": timezone_name,
    }
    job_name = f"Agent app: {display_name}"
    job_prompt = f"Scheduled run for agent app {app_name}"
    job_id = existing.get("cron_job_id")

    if job_id and cron_jobs.get_job(job_id) is None:
        job_id = None

    if job_id:
        cron_jobs.update_job(
            job_id,
            {
                "schedule": cron,
                "name": job_name,
                "prompt": job_prompt,
                "job_type": "agent_app_run",
                "payload": payload,
            },
        )
        if enabled:
            cron_jobs.resume_job(job_id)
        else:
            cron_jobs.pause_job(job_id)
    else:
        job = cron_jobs.create_job(
            prompt=job_prompt,
            schedule=cron,
            name=job_name,
            deliver="local",
        )
        job_id = job["id"]
        cron_jobs.update_job(
            job_id,
            {
                "job_type": "agent_app_run",
                "payload": payload,
            },
        )
        if not enabled:
            cron_jobs.pause_job(job_id)

    row = {
        "cron_job_id": job_id,
        "cron": cron,
        "timezone": timezone_name,
        "inputs": inputs,
        "enabled": enabled,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    schedules[app_name] = row
    _save_schedules(schedules)
    return row


def delete_schedule(app_name: str) -> bool:
    schedules = _load_schedules()
    row = schedules.pop(app_name, None)
    if row is None:
        return False
    _save_schedules(schedules)
    job_id = row.get("cron_job_id")
    if job_id:
        cron_jobs = _cron_jobs_module()
        cron_jobs.remove_job(job_id)
    return True


def get_webhook(app_name: str, *, request_base: str | None = None) -> dict[str, Any] | None:
    store = _load_webhook_store()
    row = store["apps"].get(app_name)
    if not row:
        return None
    token_last4 = row.get("token_last4", "????")
    return {
        "configured": True,
        "url": f"{public_base_url(request_base)}/api/public/agent-apps/hooks/****{token_last4}",
        "token_last4": token_last4,
        "created_at": row.get("created_at"),
    }


def rotate_webhook(app_name: str, *, request_base: str | None = None) -> dict[str, Any]:
    registry = get_agent_app_registry()
    if registry.get(app_name) is None:
        raise ValueError(f"Agent app not installed: {app_name}")
    store = _load_webhook_store()
    old = store["apps"].pop(app_name, None)
    if old and old.get("token"):
        store["tokens"].pop(old["token"], None)
    token = secrets.token_urlsafe(32)
    created_at = datetime.now(timezone.utc).isoformat()
    store["apps"][app_name] = {
        "token": token,
        "token_last4": token[-4:],
        "created_at": created_at,
    }
    store["tokens"][token] = app_name
    _save_webhook_store(store)
    url = f"{public_base_url(request_base)}/api/public/agent-apps/hooks/{token}"
    return {
        "url": url,
        "token_last4": token[-4:],
        "created_at": created_at,
    }


def delete_webhook(app_name: str) -> bool:
    store = _load_webhook_store()
    row = store["apps"].pop(app_name, None)
    if row is None:
        return False
    token = row.get("token")
    if token:
        store["tokens"].pop(token, None)
    _save_webhook_store(store)
    return True


def _hour_bucket(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.replace(minute=0, second=0, microsecond=0).isoformat()


def _check_rate_limit(store: dict[str, Any], app_name: str) -> None:
    row = store["apps"].get(app_name) or {}
    bucket = row.get("rate_bucket")
    count = int(row.get("rate_count") or 0)
    current_bucket = _hour_bucket()
    if bucket != current_bucket:
        row["rate_bucket"] = current_bucket
        row["rate_count"] = 0
        count = 0
    limit = webhook_rate_limit()
    if count >= limit:
        raise PermissionError("agent_app.webhook_rate_limit")
    row["rate_count"] = count + 1
    store["apps"][app_name] = row
    _save_webhook_store(store)


def resolve_webhook_app(token: str) -> str | None:
    store = _load_webhook_store()
    app_name = store["tokens"].get(token)
    if not app_name:
        return None
    if get_agent_app_registry().get(app_name) is None:
        return None
    return app_name


def execute_agent_app_job(payload: dict[str, Any]) -> dict[str, Any]:
    app_name = str(payload.get("app_name") or "").strip()
    if not app_name:
        raise ValueError("payload.app_name is required")
    app_dir = get_agent_app_registry().app_dir(app_name)
    if app_dir is None:
        raise ValueError(f"Agent app not installed: {app_name}")
    inputs = payload.get("inputs") or {}
    if not isinstance(inputs, dict):
        inputs = {}
    context = {"form": inputs}
    input_text = str(payload.get("input") or "")
    runner = str(payload.get("runner") or "scheduled").lower()
    if runner == "api":
        return run_api(app_dir, input_text=input_text, context=context)
    return run_scheduled(app_dir, input_text=input_text, context=context)


def run_webhook_token(
    token: str,
    *,
    input_text: str = "",
    inputs: dict[str, Any] | None = None,
    client_ip: str | None = None,
) -> dict[str, Any]:
    if not webhook_ip_allowed(client_ip):
        raise PermissionError("agent_app.webhook_ip_denied")
    app_name = resolve_webhook_app(token)
    if app_name is None:
        raise LookupError("invalid webhook token")
    store = _load_webhook_store()
    _check_rate_limit(store, app_name)
    payload = {
        "app_name": app_name,
        "inputs": inputs or {},
        "input": input_text,
        "runner": "api",
    }
    return execute_agent_app_job(payload)


def cleanup_app_automation(app_name: str) -> None:
    delete_schedule(app_name)
    delete_webhook(app_name)


def cron_job_source(job: dict[str, Any]) -> dict[str, str] | None:
    if job.get("job_type") != "agent_app_run":
        return None
    payload = job.get("payload") or {}
    app_name = str(payload.get("app_name") or "").strip()
    if not app_name:
        return None
    display = app_name
    row = get_agent_app_registry().get(app_name)
    if row:
        display = str(row.get("display_name") or app_name)
    return {
        "label": f"Agent app: {display}",
        "href": f"/agent-apps/{app_name}",
        "app_name": app_name,
    }
