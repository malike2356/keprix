"""Customer Concierge setup and publish (Prompt 628).

Keprix-native only. No Carina runtime dependency.
"""

from __future__ import annotations

from keprix.customer_concierge.prompt_overlay import build_concierge_persona_overlay
from keprix.customer_concierge.readiness import evaluate_readiness
from keprix.customer_concierge.store import ConciergeProfileStore, get_concierge_store

PRODUCT = "keprix"
CARINA_RUNTIME_REQUIRED = False

__all__ = [
    "CARINA_RUNTIME_REQUIRED",
    "PRODUCT",
    "ConciergeProfileStore",
    "build_concierge_persona_overlay",
    "evaluate_readiness",
    "get_concierge_store",
]
