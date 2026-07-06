"""SWE-agent and Aider-style coding agent modules."""

from keprix.coding.benchmark import run_benchmark
from keprix.coding.chat_loop import CodingChatRequest, CodingChatResult, run_coding_chat
from keprix.coding.configs import CodingProfile, list_profiles, load_profile
from keprix.coding.context_loader import LoadedContext, load_context
from keprix.coding.git_workflow import show_diff, stage_files, commit_changes
from keprix.coding.issue_runner import IssueRunRequest, IssueRunResult, run_issue
from keprix.coding.repo_map import RepoMap, build_repo_map
from keprix.coding.trajectory import TrajectoryLogger
from keprix.coding.voice_to_code import voice_to_coding_request
from keprix.coding.web_chat_export import export_web_chat_bundle

__all__ = [
    "CodingChatRequest",
    "CodingChatResult",
    "CodingProfile",
    "IssueRunRequest",
    "IssueRunResult",
    "LoadedContext",
    "RepoMap",
    "TrajectoryLogger",
    "build_repo_map",
    "commit_changes",
    "export_web_chat_bundle",
    "list_profiles",
    "load_context",
    "load_profile",
    "run_benchmark",
    "run_coding_chat",
    "run_issue",
    "show_diff",
    "stage_files",
    "voice_to_coding_request",
]
