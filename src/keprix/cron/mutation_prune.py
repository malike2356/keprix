"""Cron entry point for daily mutation pruning (Prompt 154)."""

from __future__ import annotations

import logging

from keprix.mutation.retention import prune_mutations_if_due

logger = logging.getLogger(__name__)


def run_mutation_prune_job(*, workspace_id: str = "default") -> dict:
    """Invoke mutation pruning; suitable for cron job handlers."""
    pruned = prune_mutations_if_due(workspace_id=workspace_id, force=True)
    logger.info("mutation prune cron job pruned %d mutations", pruned)
    return {"pruned": pruned}
