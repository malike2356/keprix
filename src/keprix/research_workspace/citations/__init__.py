"""Citation brain for research workflows."""

from keprix.research_workspace.citations.bibliography import export_bibliography
from keprix.research_workspace.citations.literature_notes import generate_literature_note
from keprix.research_workspace.citations.models import CitationRecord
from keprix.research_workspace.citations.zotero_api import ZoteroClient, ZoteroSettingsStore

__all__ = [
    "CitationRecord",
    "ZoteroClient",
    "ZoteroSettingsStore",
    "export_bibliography",
    "generate_literature_note",
]
