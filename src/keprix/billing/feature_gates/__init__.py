"""Feature gate enforcement for plan-based access control."""

from keprix.billing.feature_gates.enforcer import check_feature, require_feature
from keprix.billing.feature_gates.matrix import build_feature_matrix

__all__ = ["check_feature", "require_feature", "build_feature_matrix"]
