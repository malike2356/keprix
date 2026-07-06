"""Shared table column definitions for dashboard surfaces."""

from __future__ import annotations

TABLE_COLUMNS: dict[str, list[dict[str, str]]] = {
    "memory": [
        {"id": "content", "label": "Content", "width": "50%"},
        {"id": "tags", "label": "Tags", "width": "20%"},
        {"id": "created_at", "label": "Created", "width": "20%"},
    ],
    "skills": [
        {"id": "name", "label": "Skill", "width": "25%"},
        {"id": "category", "label": "Category", "width": "20%"},
        {"id": "description", "label": "Description", "width": "40%"},
        {"id": "enabled", "label": "Enabled", "width": "15%"},
    ],
    "research_tasks": [
        {"id": "query", "label": "Query", "width": "40%"},
        {"id": "status", "label": "Status", "width": "15%"},
        {"id": "progress_pct", "label": "Progress", "width": "15%"},
        {"id": "started_at", "label": "Started", "width": "20%"},
    ],
    "datasets": [
        {"id": "name", "label": "Name", "width": "30%"},
        {"id": "format", "label": "Format", "width": "15%"},
        {"id": "row_count", "label": "Rows", "width": "15%"},
        {"id": "created_at", "label": "Imported", "width": "25%"},
    ],
}
