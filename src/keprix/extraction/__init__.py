"""Legacy platform feature extraction and boundary tooling."""

from keprix.extraction.classifier import FeatureClass, classify_feature, is_governance_gated
from keprix.extraction.report import build_boundary_report, load_inventory, validate_inventory

__all__ = [
    "FeatureClass",
    "classify_feature",
    "is_governance_gated",
    "build_boundary_report",
    "load_inventory",
    "validate_inventory",
]
