"""CODEX legal assistant persona package."""

from keprix.personas.codex.drafter import CodexDrafter, DraftDocument
from keprix.personas.codex.persona import CODEX_PERSONA
from keprix.personas.codex.researcher import CodexResearcher, LegalAnswer, RegulatoryUpdate
from keprix.personas.codex.reviewer import ClauseFinding, CodexReviewer, ContractReview

__all__ = [
    "CODEX_PERSONA",
    "ClauseFinding",
    "CodexDrafter",
    "CodexResearcher",
    "CodexReviewer",
    "ContractReview",
    "DraftDocument",
    "LegalAnswer",
    "RegulatoryUpdate",
]
