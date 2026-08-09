"""Customer Concierge (Prompts 628+).

Keprix-native only. No Carina runtime dependency.
"""

from __future__ import annotations

from keprix.customer_concierge.capability_health import evaluate_capability_health
from keprix.customer_concierge.contract_types import CUSTOMER_CONCIERGE_CONTRACT_VERSION
from keprix.customer_concierge.prompt_overlay import build_concierge_persona_overlay
from keprix.customer_concierge.readiness import evaluate_readiness
from keprix.customer_concierge.store import ConciergeProfileStore, get_concierge_store

PRODUCT = "keprix"
CARINA_RUNTIME_REQUIRED = False

__all__ = [
    "CARINA_RUNTIME_REQUIRED",
    "CUSTOMER_CONCIERGE_CONTRACT_VERSION",
    "PRODUCT",
    "ConciergeProfileStore",
    "build_concierge_persona_overlay",
    "evaluate_capability_health",
    "evaluate_readiness",
    "get_concierge_store",
]
