"""Machine-readable product discovery for AI agents and crawlers."""

from __future__ import annotations

from keprix.product_discovery.filter import evaluate_buy_decision
from keprix.product_discovery.install_manifest import build_install_manifest
from keprix.product_discovery.schema_markup import build_json_ld_graph
from keprix.product_discovery.spec import SPEC_VERSION, build_product_spec

__all__ = [
    "SPEC_VERSION",
    "build_install_manifest",
    "build_json_ld_graph",
    "build_product_spec",
    "evaluate_buy_decision",
]
