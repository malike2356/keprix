"""Legacy vault purge with backup."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.proxy.migrate import migration_health
from keprix.proxy.paths import local_vault_path


def purge_legacy_vault(*, confirm: bool = False) -> dict[str, Any]:
    health = migration_health()
    if not confirm:
        return {"purged": False, "requires_confirmation": True, "health": health}
    path = local_vault_path()
    if not path.is_file():
        return {"purged": False, "backup_path": None, "health": health}
    backup = path.with_name(f"{path.name}.bak.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(path, backup)
    path.unlink()
    return {"purged": True, "backup_path": str(backup), "health": health}
