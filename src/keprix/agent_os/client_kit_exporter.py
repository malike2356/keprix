"""Build Agent OS client kit zip bundles."""

from __future__ import annotations

import json
import re
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from keprix.agent_os.action_board_store import ActionBoardStore
from keprix.config.constants import PRODUCT_VERSION
from keprix_constants import get_keprix_home


SECRET_RE = re.compile(r"(?:env|secret|vault)[:._-]?([A-Z][A-Z0-9_]{2,})|\$\{([A-Z][A-Z0-9_]{2,})\}")


@dataclass
class ClientKitExport:
    path: Path
    manifest: dict[str, Any]
    secrets: list[str]


def _kit_name(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in name.strip()).strip("-") or "client"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"client-kit-{safe}-{date}.zip"


def _collect_secrets(text: str) -> set[str]:
    keys: set[str] = set()
    for match in SECRET_RE.finditer(text):
        key = match.group(1) or match.group(2)
        if key:
            keys.add(key)
    return keys


class ClientKitExporter:
    def preview(self, *, user_id: str = "default", include_workspace_template: bool = True) -> dict[str, Any]:
        board = ActionBoardStore().load(user_id)
        cron_jobs = _list_cron_jobs_current_home()
        playbooks = sorted((get_keprix_home() / "playbooks" / "promoted").glob("*.yaml"))
        agent_apps = sorted((get_keprix_home() / "agent-apps").glob("*/agent.yaml"))
        secrets = self._referenced_secrets(cron_jobs, playbooks, agent_apps)
        return {
            "pins": len(board.pins),
            "cron_jobs": len(cron_jobs),
            "playbooks": [path.stem for path in playbooks],
            "agent_apps": [path.parent.name for path in agent_apps],
            "include_workspace_template": include_workspace_template,
            "secrets": sorted(secrets),
        }

    def export(self, *, name: str, output: str | Path | None = None, user_id: str = "default", include_workspace_template: bool = True) -> ClientKitExport:
        output_path = Path(output) if output else Path(tempfile.gettempdir()) / _kit_name(name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        board = ActionBoardStore().load(user_id).to_dict()
        cron_jobs = _list_cron_jobs_current_home()
        playbooks = sorted((get_keprix_home() / "playbooks" / "promoted").glob("*.yaml"))
        agent_apps = sorted((get_keprix_home() / "agent-apps").glob("*/agent.yaml"))
        secrets = sorted(self._referenced_secrets(cron_jobs, playbooks, agent_apps))
        manifest = {
            "kit_version": 1,
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "keprix_min_version": PRODUCT_VERSION,
            "counts": {
                "pins": len(board.get("pins") or []),
                "cron_jobs": len(cron_jobs),
                "playbooks": len(playbooks),
                "agent_apps": len(agent_apps),
            },
        }
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("action-board.json", json.dumps(board, indent=2))
            for job in cron_jobs:
                zf.writestr(f"automations/cron/{job['id']}.json", json.dumps(job, indent=2))
            for path in playbooks:
                zf.write(path, f"automations/playbooks/{path.name}")
            for manifest_path in agent_apps:
                app_root = manifest_path.parent
                for rel in ("agent.yaml", "instructions.md", "README.md"):
                    file_path = app_root / rel
                    if file_path.exists():
                        zf.write(file_path, f"automations/agent-apps/{app_root.name}/{rel}")
            if include_workspace_template:
                zf.writestr("workspace-template/template.json", json.dumps({"template": "client_delivery"}, indent=2))
            zf.writestr("KEPRIX.md", f"# {name} client kit\n\nOpen Agent OS and run pinned actions.\n")
            zf.writestr("SECRETS_CHECKLIST.md", self._secrets_checklist(secrets))
            zf.writestr("SETUP.md", self._setup_doc(name))
        return ClientKitExport(path=output_path, manifest=manifest, secrets=secrets)

    def _referenced_secrets(self, cron_jobs: list[dict[str, Any]], playbooks: list[Path], agent_apps: list[Path]) -> set[str]:
        secrets: set[str] = set()
        for job in cron_jobs:
            secrets.update(_collect_secrets(json.dumps(job)))
        for path in playbooks:
            secrets.update(_collect_secrets(path.read_text(encoding="utf-8")))
        for manifest_path in agent_apps:
            text = manifest_path.read_text(encoding="utf-8")
            secrets.update(_collect_secrets(text))
            data = yaml.safe_load(text) or {}
            for key in data.get("required_env") or []:
                secrets.add(str(key))
        return secrets

    def _secrets_checklist(self, secrets: list[str]) -> str:
        if not secrets:
            return "# Secrets checklist\n\nNo required secrets were detected in bundled automations.\n"
        lines = ["# Secrets checklist", "", "Add these keys to the target vault or environment before running the kit:", ""]
        lines.extend(f"- [ ] `{key}`" for key in secrets)
        return "\n".join(lines) + "\n"

    def _setup_doc(self, name: str) -> str:
        return f"# Setup {name}\n\n1. Import the kit in Settings > Agent OS > Client kit.\n2. Complete `SECRETS_CHECKLIST.md`.\n3. Open `/agent-os` and test each pinned action.\n4. Enable simplified mode for recipients when ready.\n"


def _list_cron_jobs_current_home() -> list[dict[str, Any]]:
    path = get_keprix_home() / "cron" / "jobs.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return list(data) if isinstance(data, list) else []
