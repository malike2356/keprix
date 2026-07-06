"""Known project index for builder discovery (Keprix core only)."""

from __future__ import annotations

from typing import Any

KNOWN_PROJECTS: dict[str, dict[str, Any]] = {
    "keprix": {
        "path": "keprix",
        "stack_type": "python-fastapi",
        "tech_stack": ["python", "typescript"],
        "keprix_app": True,
    },
}

PROJECT_PATTERNS = {
    "database": "Database naming convention: projectname_db",
    "php_helpers": "Custom PHP apps often use includes/functions.php and modules/ layout",
}
