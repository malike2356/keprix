"""Workspace-scoped CRM core (programme 429-450)."""

from keprix.crm.bootstrap import ensure_crm_tables
from keprix.crm.identity import ExactMatch, FuzzyCandidate, IdentityResolver
from keprix.crm.models import (
    ALL_STAGES,
    FORWARD_STAGES,
    TERMINAL_STAGES,
    ContactabilityVerdict,
    CrmStage,
    EntityType,
    MergeSuggestionStatus,
    OutboxStatus,
    ProvenanceKind,
)
from keprix.crm.store import ConflictError, CrmStore, get_crm_store, reset_crm_store_for_tests

__all__ = [
    "ALL_STAGES",
    "FORWARD_STAGES",
    "TERMINAL_STAGES",
    "ConflictError",
    "ContactabilityVerdict",
    "CrmStage",
    "CrmStore",
    "EntityType",
    "ExactMatch",
    "FuzzyCandidate",
    "IdentityResolver",
    "MergeSuggestionStatus",
    "OutboxStatus",
    "ProvenanceKind",
    "ensure_crm_tables",
    "get_crm_store",
    "reset_crm_store_for_tests",
]
