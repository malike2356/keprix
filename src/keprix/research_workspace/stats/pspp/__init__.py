"""PSPP CLI integration for research workspace."""

from keprix.research_workspace.stats.pspp.runner import PsppRunner, detect_pspp
from keprix.research_workspace.stats.pspp.syntax import generate_analysis_syntax

__all__ = ["PsppRunner", "detect_pspp", "generate_analysis_syntax"]
