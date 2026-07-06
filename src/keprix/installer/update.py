"""Release update helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx

from keprix.config.constants import PRODUCT_VERSION
from keprix.installer.paths import get_update_state_file

GITHUB_RELEASES_URL = "https://api.github.com/repos/malike2356/keprix/releases/latest"


def parse_version(value: str) -> tuple[int, ...]:
    numbers = [int(part) for part in re.findall(r"\d+", value)]
    return tuple(numbers) if numbers else (0,)


def compare_versions(installed: str, latest: str) -> int:
    """Return -1 if installed < latest, 0 if equal, 1 if installed > latest."""
    left = parse_version(installed)
    right = parse_version(latest)
    if left == right:
        return 0
    return -1 if left < right else 1


def fetch_latest_release(url: str = GITHUB_RELEASES_URL, client: httpx.Client | None = None) -> dict[str, Any]:
    if client is not None:
        response = client.get(url)
        response.raise_for_status()
        return response.json()
    with httpx.Client(timeout=15.0) as owned:
        response = owned.get(url)
        response.raise_for_status()
        return response.json()


def is_update_available(installed: str | None = None, release: dict[str, Any] | None = None) -> bool:
    installed_version = installed or PRODUCT_VERSION
    payload = release or fetch_latest_release()
    tag = str(payload.get("tag_name", "")).lstrip("v")
    return compare_versions(installed_version, tag) < 0


def save_rollback_state(previous_version: str, image_tags: dict[str, str]) -> None:
    path = get_update_state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "previous_version": previous_version,
        "image_tags": image_tags,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_rollback_state() -> dict[str, Any] | None:
    path = get_update_state_file()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def apply_env_version(env_path: Path, version: str) -> None:
    if not env_path.exists():
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = False
    result: list[str] = []
    for line in lines:
        if line.startswith("KEPRIX_VERSION="):
            result.append(f"KEPRIX_VERSION={version}")
            updated = True
        else:
            result.append(line)
    if not updated:
        result.append(f"KEPRIX_VERSION={version}")
    env_path.write_text("\n".join(result) + "\n", encoding="utf-8")
