"""Registration helper for the existing Keprix trigger scheduler."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from keprix_constants import get_keprix_home


def property_refresh_schedule() -> dict[str, Any]:
    """Return the weekly trigger specification used by deployment tooling."""
    return {
        "name": "Property data weekly refresh",
        "enabled": os.environ.get("KEPRIX_PROPERTY_DATA_REFRESH_ENABLED", "1") != "0",
        "schedule": os.environ.get("KEPRIX_PROPERTY_DATA_REFRESH_CRON", "0 3 * * 0"),
        "action": {"type": "tool", "name": "property_data_refresh", "arguments": {"admin": True}},
    }


def ensure_weekly_refresh_job() -> dict[str, Any] | None:
    """Install one idempotent script-only job in Keprix's existing cron store."""
    if os.environ.get("KEPRIX_PROPERTY_DATA_REFRESH_ENABLED", "1") == "0":
        return None
    from cron.jobs import create_job, list_jobs

    name = "Property data weekly refresh"
    for job in list_jobs(include_disabled=True):
        if job.get("name") == name:
            return job
    scripts_dir = get_keprix_home() / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_path = scripts_dir / "property_data_refresh.py"
    script_path.write_text(
        "from keprix.property_data.refresh import refresh_all\n"
        "import json\n"
        "print(json.dumps(refresh_all(), default=str))\n",
        encoding="utf-8",
    )
    return create_job(
        prompt="",
        schedule=os.environ.get("KEPRIX_PROPERTY_DATA_REFRESH_CRON", "0 3 * * 0"),
        name=name,
        deliver="local",
        script=script_path.name,
        no_agent=True,
    )


def ensure_saved_search_job() -> dict[str, Any] | None:
    """Install one weekly script job for all active saved searches."""
    if os.environ.get("KEPRIX_PROPERTY_SAVED_SEARCH_ENABLED", "1") == "0":
        return None
    from cron.jobs import create_job, list_jobs

    name = "Property saved searches weekly run"
    for job in list_jobs(include_disabled=True):
        if job.get("name") == name:
            return job
    scripts_dir = get_keprix_home() / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "property_saved_searches.py").write_text(
        "from keprix.property_data.saved_searches import run_all_active_saved_searches\n"
        "import json\n"
        "print(json.dumps(run_all_active_saved_searches(), default=str))\n",
        encoding="utf-8",
    )
    return create_job(prompt="", schedule=os.environ.get("KEPRIX_PROPERTY_SAVED_SEARCH_CRON", "0 4 * * 0"), name=name, deliver="local", script="property_saved_searches.py", no_agent=True)
