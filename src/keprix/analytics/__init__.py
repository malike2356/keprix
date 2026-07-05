"""TaskWeaver-style analytics workspace for Keprix."""

from keprix.analytics.code_interpreter import AnalyticsSession, CodeInterpreter, analytics_interpreter
from keprix.analytics.code_verifier import CodeVerifier, VerificationResult
from keprix.analytics.container_executor import ContainerExecutor, ExecutionResult
from keprix.analytics.dataframe_memory import DataFrameMemory, DataFrameSchema
from keprix.analytics.experience_store import Experience, ExperienceStore
from keprix.analytics.notebooks import export_notebook
from keprix.analytics.planner import AnalyticsPlan, AnalyticsPlanner
from keprix.analytics.plugin_runner import PluginRunner
from keprix.analytics.reflective_execution import ReflectiveExecutor, RevisionTrail
from keprix.analytics.reports import generate_report
from keprix.analytics.statistical_methods import describe

__all__ = [
    "AnalyticsPlan",
    "AnalyticsPlanner",
    "AnalyticsSession",
    "CodeInterpreter",
    "CodeVerifier",
    "ContainerExecutor",
    "DataFrameMemory",
    "DataFrameSchema",
    "ExecutionResult",
    "Experience",
    "ExperienceStore",
    "PluginRunner",
    "ReflectiveExecutor",
    "RevisionTrail",
    "VerificationResult",
    "analytics_interpreter",
    "describe",
    "export_notebook",
    "generate_report",
]
