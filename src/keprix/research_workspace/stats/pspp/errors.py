"""PSPP integration errors."""

from __future__ import annotations

from keprix.research_workspace.errors import ResearchWorkspaceError


class PSPPError(ResearchWorkspaceError):
    pass


class PSPPNotInstalledError(PSPPError):
    pass


class PSPPSyntaxError(PSPPError):
    pass


class PSPPPathNotAllowedError(PSPPError):
    pass


class PSPPUnsafeFragmentError(PSPPError):
    pass


class PSPPRunError(PSPPError):
    pass
