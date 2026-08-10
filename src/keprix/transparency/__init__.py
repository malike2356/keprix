"""EU AI Act SGI transparency: labeling, generation log, and consent gates."""

from __future__ import annotations

from keprix.transparency.consent_gate import ConsentGate, ConsentRequiredError
from keprix.transparency.generation_log import GenerationLogStore
from keprix.transparency.labels import SgiLabeler
from keprix.transparency.pipeline import finalize_ai_output, prepare_ai_call

__all__ = [
    "ConsentGate",
    "ConsentRequiredError",
    "GenerationLogStore",
    "SgiLabeler",
    "finalize_ai_output",
    "prepare_ai_call",
]
