"""Workspace domain exceptions."""

from __future__ import annotations


class WorkspaceError(Exception):
    pass


class NotFoundError(WorkspaceError):
    pass


class PermissionDeniedError(WorkspaceError):
    pass
