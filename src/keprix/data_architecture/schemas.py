"""Canonical IDs and plane contracts for keprix data architecture."""

from __future__ import annotations

from keprix.compat import StrEnum
from typing import TypedDict


class StoragePlane(StrEnum):
    CONTROL = "control_plane"
    DATA = "data_plane"
    RESEARCH = "research_plane"
    RETRIEVAL = "retrieval_plane"


class CanonicalIds(TypedDict, total=False):
    tenant_id: str
    workspace_id: str
    app_id: str
    agent_id: str
    user_id: str
    session_id: str
    dataset_id: str
    research_project_id: str
    job_id: str
    artifact_id: str
    source_id: str
    claim_id: str
    citation_id: str


JOB_TYPES = frozenset(
    {
        "agent_task",
        "deep_research",
        "data_import",
        "data_cleaning",
        "statistical_analysis",
        "ml_training",
        "model_evaluation",
        "report_generation",
        "obsidian_sync",
        "embedding_refresh",
        "billing_rollup",
        "analytics_rollup",
        "governance_policy_check",
    }
)
