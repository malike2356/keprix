"""Resolve workspace documents and notes for export."""

from __future__ import annotations

from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo


def resolve_workspace_content(input_type: str, content_id: str, user_key: str) -> str:
    user = {"id": user_key, "username": user_key}
    if input_type == "document_id":
        doc = workspace_repo.get_document(user, content_id)
        title = doc.get("title", "")
        body = doc.get("content", "")
        return f"# {title}\n\n{body}" if title else str(body)
    if input_type == "note_id":
        note = workspace_repo.get_note(user, content_id)
        title = note.get("title", "")
        body = note.get("content", "")
        return f"# {title}\n\n{body}" if title else str(body)
    raise ValueError(f"Unsupported resolver input_type: {input_type}")


def make_document_resolver(user_key: str):
    def _resolver(content_id: str) -> str:
        try:
            return resolve_workspace_content("document_id", content_id, user_key)
        except NotFoundError:
            return resolve_workspace_content("note_id", content_id, user_key)

    return _resolver
