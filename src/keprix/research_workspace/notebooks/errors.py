"""Notebook computation lane errors."""

from __future__ import annotations

from keprix.research_workspace.errors import ResearchWorkspaceError


class NotebookError(ResearchWorkspaceError):
    pass


class DangerousCodeError(NotebookError):
    pass


class RunnerNotInstalledError(NotebookError):
    pass


class SandboxError(NotebookError):
    pass


class NotebookRunError(NotebookError):
    pass
