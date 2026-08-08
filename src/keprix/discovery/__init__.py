"""Keprix discovery: pluggable adapters that produce LeadCandidates and CRM jobs.

Architecture lock: this package is under ``keprix.discovery`` (not capability_mesh).
CRM Lists are created via ``keprix.crm.store``. Soft Wall gates list materialize.
Discovery never implies contactability or outreach rights.
"""

from __future__ import annotations

from keprix.discovery.materialize import (
    enroll_requires_soft_wall,
    is_high_risk_pack,
    materialize_candidates,
)
from keprix.discovery.models import (
    AdapterHealth,
    AdapterHealthStatus,
    AdapterManifest,
    DiscoverLimits,
    DiscoverQuery,
    FieldProvenance,
    JobStatus,
    LeadCandidate,
)
from keprix.discovery.registry import (
    AdapterDisabledError,
    AdapterNotConfiguredError,
    AdapterNotFoundError,
    DiscoveryRegistry,
    get_discovery_registry,
    reset_discovery_registry_for_tests,
)
from keprix.discovery.runner import DiscoveryJobRunner, get_discovery_runner

__all__ = [
    "AdapterDisabledError",
    "AdapterHealth",
    "AdapterHealthStatus",
    "AdapterManifest",
    "AdapterNotConfiguredError",
    "AdapterNotFoundError",
    "DiscoverLimits",
    "DiscoverQuery",
    "DiscoveryJobRunner",
    "DiscoveryRegistry",
    "FieldProvenance",
    "JobStatus",
    "LeadCandidate",
    "enroll_requires_soft_wall",
    "get_discovery_registry",
    "get_discovery_runner",
    "is_high_risk_pack",
    "materialize_candidates",
    "reset_discovery_registry_for_tests",
]


def bootstrap_discovery() -> None:
    """Register adapters and vertical packs (safe to call multiple times)."""
    get_discovery_registry().ensure_builtin()
    from keprix.discovery.adapters import bootstrap_packs

    bootstrap_packs()
