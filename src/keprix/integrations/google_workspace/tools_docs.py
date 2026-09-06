"""Google Docs tool wrappers."""

from typing import Any

from .bridge import GoogleWorkspaceBridge


def gws_docs_create(title: str, text: str = "", confirm: bool = False) -> dict[str, Any]:
    return GoogleWorkspaceBridge().docs_create(title, text, confirm)


def gws_docs_update(
    document_id: str, text: str, replace: bool = False, confirm: bool = False
) -> dict[str, Any]:
    return GoogleWorkspaceBridge().docs_update(document_id, text, replace=replace, confirm=confirm)
