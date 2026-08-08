"""Project registry: loaded manifests, grants, kill switches, budgets (KUS)."""

from __future__ import annotations

import json
import os
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from keprix.universal_sidecar.manifest.validate import digest_manifest, load_manifest, validate_manifest


class ProjectRegistry:
    """In-process registry of applied project manifests and runtime state."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._lock = threading.RLock()
        self._projects: dict[str, dict[str, Any]] = {}
        self._kill: dict[str, dict[str, Any]] = {}
        self._budgets: dict[str, dict[str, Any]] = {}
        self._budget_usage: dict[str, dict[str, float]] = {}
        self._persistence_explicit = path is not None
        self.path = Path(path) if path else self._default_path()
        self._load_persisted()

    @staticmethod
    def _default_path() -> Path:
        configured = os.environ.get("KEPRIX_SIDECAR_REGISTRY_PATH", "").strip()
        if configured:
            return Path(configured).expanduser()
        try:
            from keprix.auth.config import data_dir

            root = Path(data_dir())
        except Exception:
            root = Path.home() / ".keprix"
        return root / "universal_sidecar" / "projects.json"

    def _load_persisted(self) -> None:
        if (
            os.environ.get("PYTEST_CURRENT_TEST")
            and not self._persistence_explicit
            and not os.environ.get("KEPRIX_SIDECAR_REGISTRY_PATH")
        ):
            return
        if not self.path.is_file():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for item in payload.get("projects") or []:
            manifest = item.get("manifest") if isinstance(item, dict) else None
            if not isinstance(manifest, dict) or not validate_manifest(manifest).ok:
                continue
            key = str(manifest["project_key"])
            self._projects[key] = {
                "manifest": deepcopy(manifest),
                "digest": digest_manifest(manifest),
                "applied_at": float(item.get("applied_at") or time.time()),
                "enabled": bool(item.get("enabled", True)),
                "grants": self._default_grants(manifest),
            }
            self._budgets[key] = dict(manifest.get("budgets") or {})
            kill = item.get("kill") if isinstance(item.get("kill"), dict) else {}
            self._kill[key] = {
                "project": bool(kill.get("project")),
                "connector": bool(kill.get("connector")),
                "callbacks": bool(kill.get("callbacks")),
                "memory_writes": bool(kill.get("memory_writes")),
                "nodes": set(kill.get("nodes") or []),
            }

    def _persist(self) -> None:
        if (
            os.environ.get("PYTEST_CURRENT_TEST")
            and not self._persistence_explicit
            and not os.environ.get("KEPRIX_SIDECAR_REGISTRY_PATH")
        ):
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        projects = []
        for key, row in sorted(self._projects.items()):
            kill = dict(self._kill.get(key) or {})
            kill["nodes"] = sorted(kill.get("nodes") or [])
            projects.append(
                {
                    "manifest": deepcopy(row["manifest"]),
                    "applied_at": row["applied_at"],
                    "enabled": row["enabled"],
                    "kill": kill,
                }
            )
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"version": 1, "projects": projects}, indent=2), encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(self.path)

    def reset_for_tests(self) -> None:
        with self._lock:
            self._projects.clear()
            self._kill.clear()
            self._budgets.clear()
            self._budget_usage.clear()

    def apply(
        self,
        manifest: dict[str, Any],
        *,
        confirm_risky: bool = False,
        previous: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = validate_manifest(manifest)
        if not result.ok:
            raise ValueError(json.dumps(result.as_dict()))
        from keprix.universal_sidecar.manifest.validate import diff_manifests

        if previous:
            diff = diff_manifests(previous, manifest)
            if diff.get("requires_explicit_apply") and not confirm_risky:
                raise PermissionError("risky_changes_require_confirm:" + ",".join(diff["risky_changes"]))
        key = str(manifest["project_key"])
        with self._lock:
            row = {
                "manifest": deepcopy(manifest),
                "digest": result.digest,
                "applied_at": time.time(),
                "enabled": True,
                "grants": self._default_grants(manifest),
            }
            self._projects[key] = row
            self._budgets[key] = dict(manifest.get("budgets") or {})
            self._kill.setdefault(
                key,
                {
                    "project": False,
                    "connector": False,
                    "callbacks": False,
                    "memory_writes": False,
                    "nodes": set(),
                },
            )
            self._persist()
            return {"project_key": key, "digest": result.digest, "applied": True}

    @staticmethod
    def _default_grants(manifest: dict[str, Any]) -> set[str]:
        grants = {"discover", "jobs", "events", "approvals", "metrics"}
        for cap in manifest.get("capabilities") or []:
            node = cap.get("node")
            if node:
                grants.add(f"invoke:{node}")
            for scope in cap.get("scopes") or []:
                grants.add(str(scope))
        for op in manifest.get("connectors") or []:
            key = op.get("key")
            if key:
                grants.add(f"connector:{key}")
        memory = (manifest.get("memory") or {}).get("mode", "ephemeral")
        if memory != "disabled":
            grants.add("memory:ephemeral/read")
            grants.add("memory:ephemeral/write")
        return grants

    def load_file(self, path: str | Path, *, confirm_risky: bool = False) -> dict[str, Any]:
        manifest = load_manifest(path)
        previous = None
        key = str(manifest.get("project_key") or "")
        with self._lock:
            if key in self._projects:
                previous = self._projects[key]["manifest"]
        return self.apply(manifest, confirm_risky=confirm_risky, previous=previous)

    def get(self, project_key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._projects.get(project_key)
            return deepcopy(row) if row else None

    def require(self, project_key: str) -> dict[str, Any]:
        row = self.get(project_key)
        if not row:
            raise KeyError(project_key)
        return row

    def list_projects(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "project_key": k,
                    "display_name": v["manifest"].get("display_name"),
                    "digest": v["digest"],
                    "enabled": v["enabled"],
                    "environment": v["manifest"].get("environment"),
                    "deployment": v["manifest"].get("deployment"),
                }
                for k, v in sorted(self._projects.items())
            ]

    def delete(self, project_key: str) -> bool:
        with self._lock:
            if project_key not in self._projects:
                return False
            self._projects.pop(project_key, None)
            self._kill.pop(project_key, None)
            self._budgets.pop(project_key, None)
            self._budget_usage.pop(project_key, None)
            self._persist()
            return True

    def set_enabled(self, project_key: str, enabled: bool) -> None:
        with self._lock:
            self.require(project_key)
            self._projects[project_key]["enabled"] = enabled
            self._persist()

    def kill(self, project_key: str, *, switch: str, value: bool = True, node: str | None = None) -> None:
        with self._lock:
            kills = self._kill.setdefault(
                project_key,
                {"project": False, "connector": False, "callbacks": False, "memory_writes": False, "nodes": set()},
            )
            if switch == "node" and node:
                if value:
                    kills["nodes"].add(node)
                else:
                    kills["nodes"].discard(node)
            elif switch in kills:
                kills[switch] = value
            self._persist()

    def is_killed(self, project_key: str, *, switch: str = "project", node: str | None = None) -> bool:
        with self._lock:
            kills = self._kill.get(project_key) or {}
            if kills.get("project"):
                return True
            if node and node in (kills.get("nodes") or set()):
                return True
            return bool(kills.get(switch))

    def consume_budget(self, project_key: str, *, kind: str = "requests", amount: float = 1.0) -> bool:
        with self._lock:
            limits = self._budgets.get(project_key) or {}
            usage = self._budget_usage.setdefault(project_key, {})
            key = f"{kind}:{int(time.time() // 60)}"
            usage[key] = usage.get(key, 0.0) + amount
            limit_map = {
                "requests": limits.get("requests_per_minute"),
                "jobs": limits.get("jobs_concurrent"),
                "callbacks": limits.get("callback_per_hour"),
            }
            limit = limit_map.get(kind)
            if limit is None:
                return True
            return usage[key] <= float(limit)

    def grants_for(self, project_key: str) -> frozenset[str]:
        row = self.require(project_key)
        return frozenset(row.get("grants") or set())


_REGISTRY: ProjectRegistry | None = None
_LOCK = threading.Lock()


def get_project_registry() -> ProjectRegistry:
    global _REGISTRY
    with _LOCK:
        if _REGISTRY is None:
            _REGISTRY = ProjectRegistry()
        return _REGISTRY
