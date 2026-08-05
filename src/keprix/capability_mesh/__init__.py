"""Keprix capability mesh: graph spine for feature relatedness and channel readiness.

Spine remains tools.registry + toolsets. This package is the synapse layer
(nodes/edges + queries), not a second tool bus.
"""

from keprix.capability_mesh.graph import (
    CapabilityEdge,
    CapabilityGraph,
    CapabilityGraphError,
    CapabilityNode,
    default_graph_path,
    load_graph,
)
from keprix.capability_mesh.dod import FEATURE_DOD_CHECKLIST, MESH_PROMPT_TEMPLATE, assert_dod
from keprix.capability_mesh.ids import OBJECT_TYPES, resolve_booking_links
from keprix.capability_mesh.discovery import render_discovery_markdown, write_discovery

__all__ = [
    "FEATURE_DOD_CHECKLIST",
    "MESH_PROMPT_TEMPLATE",
    "CapabilityEdge",
    "CapabilityGraph",
    "CapabilityGraphError",
    "CapabilityNode",
    "OBJECT_TYPES",
    "assert_dod",
    "render_discovery_markdown",
    "resolve_booking_links",
    "write_discovery",
    "default_graph_path",
    "load_graph",
]
