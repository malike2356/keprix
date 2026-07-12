"""Default guardrails for Agent OS (Prompt 270 Task 5.4).

Restricted workspace roots, approval expectations, and vault auto-backup.
"""

from __future__ import annotations

import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.security.file_gate import FileAccessGate
from keprix.security.terminal_sandbox import POLICY_RESTRICTED, SandboxPolicy
from keprix.vault.config import get_vault_config
from keprix_constants import get_keprix_home


def guardrails_enabled() -> bool:
    raw = os.getenv("KEPRIX_GUARDRAILS_DEFAULT", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def vault_backup_enabled() -> bool:
    raw = os.getenv("KEPRIX_VAULT_AUTO_BACKUP", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def default_workspace_root() -> Path:
    override = os.getenv("KEPRIX_WORKSPACE_ROOT", "").strip()
    if override:
        path = Path(override).expanduser().resolve()
    else:
        path = (get_keprix_home() / "workspace").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_sandbox_policy(*, workspace: Path | None = None) -> SandboxPolicy:
    root = workspace or default_workspace_root()
    vault = get_vault_config().root_path
    allowed = {str(root), "/tmp"}
    if vault:
        allowed.add(str(Path(vault).expanduser().resolve()))
    policy = SandboxPolicy(
        allowed_paths=allowed,
        denied_paths=set(POLICY_RESTRICTED.denied_paths),
        deny_paths_outside_allowed=True,
        allowed_commands=set(POLICY_RESTRICTED.allowed_commands),
        denied_commands=set(POLICY_RESTRICTED.denied_commands),
        allow_egress=False,
        deny_egress_by_default=True,
        max_runtime_seconds=60,
    )
    return policy


def default_file_gate(*, workspace: Path | None = None) -> FileAccessGate:
    return FileAccessGate(default_sandbox_policy(workspace=workspace))


def approvals_required_by_default() -> bool:
    raw = os.getenv("KEPRIX_APPROVALS_MODE", "manual").strip().lower()
    return raw in {"manual", "required", "always", "true", "1", "yes"}


def backup_vault(*, reason: str = "pre-write") -> dict[str, Any]:
    """Snapshot the markdown vault before agent writes (one-vault safety)."""
    if not vault_backup_enabled():
        return {"ok": False, "skipped": True, "reason": "vault_auto_backup_disabled"}
    config = get_vault_config()
    if not config.root_path:
        return {"ok": False, "skipped": True, "reason": "vault_not_configured"}
    root = Path(config.root_path).expanduser().resolve()
    if not root.is_dir():
        return {"ok": False, "skipped": True, "reason": "vault_missing"}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_root = get_keprix_home() / "backups" / "vault"
    backup_root.mkdir(parents=True, exist_ok=True)
    archive = backup_root / f"vault_{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(root, arcname=root.name)

    # Keep last 20 snapshots.
    archives = sorted(backup_root.glob("vault_*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in archives[20:]:
        try:
            stale.unlink()
        except OSError:
            pass

    return {
        "ok": True,
        "reason": reason,
        "path": str(archive),
        "size_bytes": archive.stat().st_size,
        "vault_root": str(root),
    }


def guardrails_status() -> dict[str, Any]:
    workspace = default_workspace_root()
    return {
        "ok": True,
        "enabled": guardrails_enabled(),
        "workspace_root": str(workspace),
        "approvals_required": approvals_required_by_default(),
        "vault_auto_backup": vault_backup_enabled(),
        "sandbox": {
            "deny_outside_workspace": True,
            "allowed_paths": sorted(default_sandbox_policy(workspace=workspace).allowed_paths),
        },
        "links": {
            "approvals": "/agent-os",
            "vault": "/settings/vault",
            "readiness": "/readiness",
        },
    }


def maybe_backup_vault_before_write() -> dict[str, Any]:
    if not guardrails_enabled():
        return {"ok": False, "skipped": True, "reason": "guardrails_disabled"}
    try:
        backup_root = get_keprix_home() / "backups" / "vault"
        if backup_root.is_dir():
            archives = sorted(backup_root.glob("vault_*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
            if archives:
                age = datetime.now(timezone.utc).timestamp() - archives[0].stat().st_mtime
                min_interval = int(os.getenv("KEPRIX_VAULT_BACKUP_MIN_INTERVAL_SEC", "300"))
                if age < min_interval:
                    return {
                        "ok": True,
                        "skipped": True,
                        "reason": "throttled",
                        "path": str(archives[0]),
                        "age_seconds": int(age),
                    }
        return backup_vault(reason="pre-write")
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
