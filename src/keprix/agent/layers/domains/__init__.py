"""Domain-specific prompt layers (injected when context matches)."""

from __future__ import annotations

import re
from typing import Iterable

from agent.layers.domains.code import CODE_EXECUTION_DOMAIN_LAYER
from agent.layers.domains.legal import LEGAL_DOMAIN_LAYER
from agent.layers.domains.medical import MEDICAL_DOMAIN_LAYER
from agent.layers.domains.property import PROPERTY_DOMAIN_LAYER

_DOMAIN_LAYERS: dict[str, str] = {
    "medical": MEDICAL_DOMAIN_LAYER,
    "legal": LEGAL_DOMAIN_LAYER,
    "code": CODE_EXECUTION_DOMAIN_LAYER,
    "property": PROPERTY_DOMAIN_LAYER,
}

_MEDICAL_PATTERNS = (
    r"\b(diagnos|symptom|medication|prescri|treatment|therapy|clinical|patient)\b",
    r"\b(mental health|depression|anxiety|bipolar|psychiatr)\b",
)
_LEGAL_PATTERNS = (
    r"\b(legal|lawsuit|contract|liability|regulat|compliance|gdpr|hipaa)\b",
    r"\b(attorney|lawyer|court|statute|indemn)\b",
)
_CODE_PATTERNS = (
    r"\b(code|script|function|refactor|debug|compile|pytest|npm|pip install)\b",
    r"\b(python|typescript|javascript|rust|golang|sql)\b",
)
_PROPERTY_PATTERNS = (
    r"\b(property|rental|landlord|tenant|mortgage|yield|portfolio)\b",
    r"\b(real estate|buy-to-let|stamp duty|section 24)\b",
)


def detect_domains(text: str) -> set[str]:
    """Return domain keys suggested by *text* (system message or user hint)."""
    if not text or not text.strip():
        return set()
    lowered = text.lower()
    domains: set[str] = set()
    if any(re.search(p, lowered) for p in _MEDICAL_PATTERNS):
        domains.add("medical")
    if any(re.search(p, lowered) for p in _LEGAL_PATTERNS):
        domains.add("legal")
    if any(re.search(p, lowered) for p in _CODE_PATTERNS):
        domains.add("code")
    if any(re.search(p, lowered) for p in _PROPERTY_PATTERNS):
        domains.add("property")
    return domains


def render_domain_layers(domain_keys: Iterable[str]) -> str:
    """Join matching domain layers in stable order."""
    ordered = ("medical", "legal", "code", "property")
    parts: list[str] = []
    keys = set(domain_keys)
    for key in ordered:
        if key in keys and key in _DOMAIN_LAYERS:
            parts.append(_DOMAIN_LAYERS[key].strip())
    return "\n\n".join(parts)
