"""Generic governance bridge (kill switch, audit, policy)."""

from keprix.governance.client import get_governance_client
from keprix.governance.config import get_governance_config
from keprix.governance.kill_relay import get_kill_state
from keprix.governance.policy_receiver import get_policy_registry
from keprix.governance.store import get_governance_store

__all__ = [
    "get_kill_state",
    "get_policy_registry",
    "get_governance_client",
    "get_governance_config",
    "get_governance_store",
]
