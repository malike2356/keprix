"""Integrity checks across storage planes."""

from __future__ import annotations

from typing import Any

from keprix.data_architecture.control_plane import get_control_plane
from keprix.data_architecture.data_plane import get_workspace_data_plane
from keprix.data_architecture.retrieval_plane import retrieval_status


async def planes_integrity(workspace_id: str = "default") -> dict[str, Any]:
    control = get_control_plane().status()
    data_plane = get_workspace_data_plane(workspace_id).integrity_check()
    retrieval = await retrieval_status()
    return {
        "control_plane": control,
        "data_plane": data_plane,
        "retrieval_plane": retrieval,
        "research_plane": {"engine": "duckdb", "formats": ["csv", "parquet", "json", "jsonl"]},
    }
