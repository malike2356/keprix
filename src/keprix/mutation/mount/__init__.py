"""Mutation as plugin/skill mount (prompt 773).

Self-modification becomes a reviewed capability change: propose mount/unmount,
require human four-eyes approval, apply only through keprix.plugin_lifecycle.
"""

from __future__ import annotations

from keprix.mutation.mount.banned import (
    MountBanError,
    assert_mount_allowed,
    banned_summary,
)
from keprix.mutation.mount.intents import (
    MOUNT_ACTIONS,
    MountIntent,
    map_legacy_mutation_to_intent,
    mutation_ledger_id,
    skill_plugin_id,
)
from keprix.mutation.mount.service import (
    MountApprovalError,
    MountApplyError,
    MutationMountService,
    get_mutation_mount_service,
    reset_mutation_mount_service_for_tests,
)
from keprix.mutation.mount.store import (
    MountProposal,
    MountProposalStore,
    get_mount_proposal_store,
    reset_mount_proposal_store_for_tests,
)

__all__ = [
    "MOUNT_ACTIONS",
    "MountApprovalError",
    "MountApplyError",
    "MountBanError",
    "MountIntent",
    "MountProposal",
    "MountProposalStore",
    "MutationMountService",
    "assert_mount_allowed",
    "banned_summary",
    "get_mount_proposal_store",
    "get_mutation_mount_service",
    "map_legacy_mutation_to_intent",
    "mutation_ledger_id",
    "reset_mount_proposal_store_for_tests",
    "reset_mutation_mount_service_for_tests",
    "skill_plugin_id",
]
