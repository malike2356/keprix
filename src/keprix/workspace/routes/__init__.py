"""Workspace API routes."""

from keprix.workspace.routes.admin_wipe_routes import router as admin_wipe_router
from keprix.workspace.routes.assistant_routes import router as assistant_router
from keprix.workspace.routes.calendar_routes import router as calendar_router
from keprix.workspace.routes.document_routes import router as document_router
from keprix.workspace.routes.editor_draft_routes import router as draft_router
from keprix.workspace.routes.gallery_routes import router as gallery_router
from keprix.workspace.routes.note_routes import router as note_router
from keprix.workspace.routes.personal_routes import router as personal_router
from keprix.workspace.routes.preset_routes import router as preset_router
from keprix.workspace.routes.session_routes import router as session_router
from keprix.workspace.routes.task_routes import router as task_router

__all__ = [
    "admin_wipe_router",
    "assistant_router",
    "calendar_router",
    "document_router",
    "draft_router",
    "gallery_router",
    "note_router",
    "personal_router",
    "preset_router",
    "session_router",
    "task_router",
]
