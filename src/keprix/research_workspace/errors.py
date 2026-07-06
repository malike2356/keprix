"""Research workspace errors."""

from __future__ import annotations


class ResearchWorkspaceError(RuntimeError):
    """Base error for research workspace operations."""


class ProjectNotFoundError(ResearchWorkspaceError):
    pass


class PermissionDeniedError(ResearchWorkspaceError):
    pass


class ProvenanceError(ResearchWorkspaceError):
    pass


class ExternalToolBoundaryError(ResearchWorkspaceError):
    """Raised when keprix would replace an external specialist tool."""


class VaultPathError(ResearchWorkspaceError):
    pass


class UnsafeWriteError(ResearchWorkspaceError):
    pass


class ZoteroAPIError(ResearchWorkspaceError):
    pass
