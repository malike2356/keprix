"""Keprix Universal Sidecar (KUS): project-agnostic private integration surface.

Public contract path: ``/sidecar/v1/projects/{project_key}``.
Mounted on the main Keprix API (port 3333) or as a sidecar-only process (port 3360).

Configuration (``keprix.sidecar.yaml``) requests capabilities; installed runtime
policy is the upper bound. Manifests never grant shell, network, filesystem,
mutation, browser, code execution or outbound side effects by naming alone.
"""

from __future__ import annotations

from keprix.universal_sidecar.contract import (
    CONTRACT_NAME,
    CONTRACT_VERSION,
    DeploymentMode,
    NON_GOALS,
)

__all__ = [
    "CONTRACT_NAME",
    "CONTRACT_VERSION",
    "DeploymentMode",
    "NON_GOALS",
]
