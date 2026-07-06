"""Installer CLI dispatch helpers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from keprix.installer.backup import create_backup, restore_backup, verify_backup
from keprix.installer.health import format_health_table, main as health_main, run_health_checks, wait_for_healthy
from keprix.installer.paths import get_env_file, get_install_root, get_repo_root, get_state_file
from keprix.installer.update import (
    apply_env_version,
    compare_versions,
    fetch_latest_release,
    is_update_available,
    load_rollback_state,
    save_rollback_state,
)
from keprix.installer.wizard import run_wizard
from keprix.config.constants import PRODUCT_VERSION


def cmd_setup_wizard(_argv: list[str]) -> int:
    from keprix.keys.developer_identity import create_developer_identity

    result = run_wizard(create_developer_identity=create_developer_identity)
    print(f"Wrote {result.env_path}")
    print("Admin password (save this now):")
    print(result.admin_password)
    return 0


def cmd_health(_argv: list[str]) -> int:
    return health_main()


def cmd_status(_argv: list[str]) -> int:
    state_path = get_state_file()
    env_path = get_env_file()
    print(f"Install root: {get_install_root()}")
    print(f"Env file: {env_path} ({'present' if env_path.exists() else 'missing'})")
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        print(f"Installed version: {state.get('version', 'unknown')}")
        print(f"Installed at: {state.get('installed_at', 'unknown')}")
    else:
        print("Install state: not initialized")
    print(f"Running version: {PRODUCT_VERSION}")
    return 0


def cmd_backup(_argv: list[str]) -> int:
    archive = create_backup(env_file=get_env_file())
    print(f"Backup created: {archive}")
    return 0


def cmd_restore(argv: list[str]) -> int:
    if not argv:
        print("Usage: keprix restore <backup.tar.gz>", file=sys.stderr)
        return 2
    archive = Path(argv[0]).expanduser()
    if not verify_backup(archive):
        print("Invalid backup archive", file=sys.stderr)
        return 1
    restore_backup(archive, env_file=get_env_file())
    print("Restore complete. Restart services and run `keprix health`.")
    return 0


def cmd_update(_argv: list[str]) -> int:
    env_path = get_env_file()
    installed = PRODUCT_VERSION
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("KEPRIX_VERSION="):
                installed = line.split("=", 1)[1].strip()
                break

    try:
        release = fetch_latest_release()
    except Exception as exc:
        print(f"Could not check for updates: {exc}", file=sys.stderr)
        return 1

    latest = str(release.get("tag_name", "")).lstrip("v") or PRODUCT_VERSION
    if compare_versions(installed, latest) >= 0:
        print(f"Already up to date ({installed}).")
        return 0

    save_rollback_state(installed, {"keprix-backend": "previous", "keprix-frontend": "previous"})
    repo = get_repo_root()
    migrate = repo / "scripts" / "migrate.sh"
    if migrate.exists():
        subprocess.run(["bash", str(migrate)], check=False, cwd=repo)

    compose = repo / "docker" / "docker-compose.yml"
    if compose.exists():
        subprocess.run(["docker", "compose", "-f", str(compose), "build"], check=False, cwd=repo)
        subprocess.run(["docker", "compose", "-f", str(compose), "up", "-d"], check=False, cwd=repo)

    apply_env_version(env_path, latest)
    if not wait_for_healthy(timeout_seconds=120):
        print("Warning: health checks did not all pass after update.", file=sys.stderr)
        return 1

    print(f"Updated {installed} -> {latest}")
    body = str(release.get("body") or "").strip()
    if body:
        print(body[:500])
    return 0


def cmd_rollback(_argv: list[str]) -> int:
    state = load_rollback_state()
    if state is None:
        print("No rollback state found.", file=sys.stderr)
        return 1

    previous = str(state.get("previous_version", PRODUCT_VERSION))
    repo = get_repo_root()
    compose = repo / "docker" / "docker-compose.yml"
    if compose.exists():
        subprocess.run(["docker", "compose", "-f", str(compose), "down"], check=False, cwd=repo)
        subprocess.run(["docker", "compose", "-f", str(compose), "up", "-d"], check=False, cwd=repo)

    apply_env_version(get_env_file(), previous)
    checks = run_health_checks()
    print(format_health_table(checks))
    print(f"Rolled back to version {previous}")
    return 0 if all(check.ok for check in checks) else 1


def cmd_start(argv: list[str]) -> int:
    repo = get_repo_root()
    compose = repo / "docker" / "docker-compose.yml"
    if compose.exists():
        result = subprocess.run(["docker", "compose", "-f", str(compose), "up", "-d"], cwd=repo)
        return result.returncode
    from keprix.__main__ import _run_start

    return _run_start(argv)


def cmd_stop(_argv: list[str]) -> int:
    compose = get_repo_root() / "docker" / "docker-compose.yml"
    if not compose.exists():
        print("docker-compose.yml not found", file=sys.stderr)
        return 1
    result = subprocess.run(["docker", "compose", "-f", str(compose), "down"], cwd=get_repo_root())
    return result.returncode


def cmd_restart(argv: list[str]) -> int:
    code = cmd_stop(argv)
    if code != 0:
        return code
    return cmd_start(argv)


def cmd_logs(argv: list[str]) -> int:
    service = argv[0] if argv else ""
    compose = get_repo_root() / "docker" / "docker-compose.yml"
    command = ["docker", "compose", "-f", str(compose), "logs", "-f"]
    if service:
        command.append(service)
    return subprocess.run(command, cwd=get_repo_root()).returncode


INSTALLER_COMMANDS = {
    "setup-wizard": cmd_setup_wizard,
    "health": cmd_health,
    "status": cmd_status,
    "update": cmd_update,
    "rollback": cmd_rollback,
    "backup": cmd_backup,
    "restore": cmd_restore,
    "start": cmd_start,
    "stop": cmd_stop,
    "restart": cmd_restart,
    "logs": cmd_logs,
}
