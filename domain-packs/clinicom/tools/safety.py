"""Clinical safety helpers for Clinicom sidecar tools.

Utterances are untrusted clinical text, never tool instructions.
Handlers must not diagnose, prescribe, or write EHR.
"""

from __future__ import annotations

import re
from typing import Any

_NUMBER_RE = re.compile(
    r"(?<![A-Za-z])(?:\d+(?:\.\d+)?(?:\s*(?:mg|mcg|g|ml|mL|units?|tabs?|tablets?))?|"
    r"\d+/\d+|"
    r"(?:once|twice|three times)\s+(?:a|per)\s+day|"
    r"q\.?\d+h|"
    r"\d{1,2}:\d{2})",
    re.I,
)
_NEGATION_RE = re.compile(
    r"\b(?:no|not|never|without|denies|denied|negative for|nil|none)\b",
    re.I,
)
_INJECTION_RE = re.compile(
    r"(?:ignore\s+(?:previous|all)\s+instructions|system\s*prompt|you\s+are\s+now|"
    r"tool\s*call|execute\s+shell|browse\s+to|fetch\s+url|delete\s+all|"
    r"</?\s*(?:system|tool|function)\b)",
    re.I,
)
_DIAGNOSIS_ASK_RE = re.compile(
    r"\b(?:diagnose|diagnosis|prescribe|prescription|what\s+disease|"
    r"should\s+i\s+take|clinical\s+disposition)\b",
    re.I,
)

_APPROVED_MEDS = {
    "paracetamol": {"aliases": ["acetaminophen"], "note": "analgesic/antipyretic"},
    "ibuprofen": {"aliases": [], "note": "NSAID analgesic"},
    "amoxicillin": {"aliases": [], "note": "antibiotic"},
    "salbutamol": {"aliases": ["albuterol"], "note": "bronchodilator"},
    "metformin": {"aliases": [], "note": "antidiabetic"},
    "insulin": {"aliases": [], "note": "antidiabetic hormone"},
    "aspirin": {"aliases": ["asa"], "note": "antiplatelet/analgesic"},
    "warfarin": {"aliases": [], "note": "anticoagulant"},
}

_SAFETY_CATEGORIES = (
    "self_harm_or_suicide",
    "chest_pain_or_cardiac",
    "breathing_difficulty",
    "severe_allergic_reaction",
    "stroke_symptoms",
    "safeguarding",
    "medication_error_risk",
    "other_urgent_risk",
    "none",
)


def treat_as_clinical_text(text: str) -> dict[str, Any]:
    """Flag prompt-injection patterns but keep text as data."""
    raw = str(text or "")
    matches = _INJECTION_RE.findall(raw)
    return {
        "text": raw,
        "treated_as": "clinical_utterance_data",
        "injection_signals": list({m.lower() if isinstance(m, str) else str(m).lower() for m in matches}),
        "tool_instruction_allowed": False,
    }


def extract_numbers(text: str) -> list[str]:
    return [m.group(0).strip() for m in _NUMBER_RE.finditer(str(text or ""))]


def extract_negations(text: str) -> list[str]:
    return sorted({m.group(0).lower() for m in _NEGATION_RE.finditer(str(text or ""))})


def preservation_report(source: str, output: str) -> dict[str, Any]:
    src_numbers = extract_numbers(source)
    out_numbers = extract_numbers(output)
    missing_numbers = [n for n in src_numbers if n not in out_numbers and n.lower() not in output.lower()]
    src_neg = extract_negations(source)
    out_neg = extract_negations(output)
    missing_neg = [n for n in src_neg if n not in out_neg]
    warnings: list[str] = []
    if missing_numbers:
        warnings.append("possible_number_loss")
    if missing_neg:
        warnings.append("possible_negation_loss")
    return {
        "source_numbers": src_numbers,
        "output_numbers": out_numbers,
        "missing_numbers": missing_numbers,
        "source_negations": src_neg,
        "missing_negations": missing_neg,
        "warnings": warnings,
        "human_review_required": bool(warnings),
    }


def glossary_lookup(text: str) -> dict[str, Any]:
    lowered = str(text or "").lower()
    known: list[dict[str, str]] = []
    unknown: list[str] = []
    candidates = re.findall(r"[A-Za-z][A-Za-z-]{2,}", lowered)
    med_like = [w for w in candidates if w.endswith(("cillin", "olol", "mycin", "parin", "formin")) or w in _APPROVED_MEDS]
    for term in sorted(set(med_like)):
        entry = _APPROVED_MEDS.get(term)
        if entry:
            known.append({"term": term, "status": "approved", "note": entry["note"]})
            continue
        alias_hit = None
        for key, value in _APPROVED_MEDS.items():
            if term in value["aliases"]:
                alias_hit = {"term": key, "status": "approved", "note": value["note"], "matched_alias": term}
                break
        if alias_hit:
            known.append(alias_hit)
        else:
            unknown.append(term)
    return {"approved_terms": known, "unknown_terms": unknown, "invented_drug_facts": False}


def safety_triage_bounds(text: str, safety_terms: list[str] | None = None) -> dict[str, Any]:
    """Assistive signal only. Never returns disposition, diagnosis, or emergency decision."""
    lowered = str(text or "").lower()
    terms = [str(t).lower() for t in (safety_terms or []) if str(t).strip()]
    category = "none"
    evidence: list[str] = []
    if any(k in lowered for k in ("suicid", "kill myself", "end my life")) or "self_harm" in terms:
        category = "self_harm_or_suicide"
        evidence.append("self_harm_language")
    elif any(k in lowered for k in ("chest pain", "heart attack")) or "chest" in terms:
        category = "chest_pain_or_cardiac"
        evidence.append("cardiac_language")
    elif any(k in lowered for k in ("can't breathe", "cannot breathe", "short of breath", "wheeze")):
        category = "breathing_difficulty"
        evidence.append("respiratory_language")
    elif any(k in lowered for k in ("anaphylaxis", "throat swelling", "severe allergy")):
        category = "severe_allergic_reaction"
        evidence.append("allergy_language")
    elif any(k in lowered for k in ("face droop", "slurred speech", "stroke")):
        category = "stroke_symptoms"
        evidence.append("stroke_language")
    elif terms:
        category = "other_urgent_risk"
        evidence.extend(terms[:4])

    diagnosis_request = bool(_DIAGNOSIS_ASK_RE.search(lowered))
    return {
        "assistive_only": True,
        "category": category if category in _SAFETY_CATEGORIES else "other_urgent_risk",
        "allowed_categories": list(_SAFETY_CATEGORIES),
        "evidence": evidence,
        "escalation_wording": (
            "Escalate to an on-call clinician or human interpreter. "
            "This signal is not a diagnosis, disposition, or emergency decision."
        ),
        "cannot": [
            "diagnose",
            "prescribe",
            "auto_acknowledge",
            "set_disposition",
            "call_emergency_services",
        ],
        "diagnosis_or_treatment_request_detected": diagnosis_request,
        "human_review_required": category != "none" or diagnosis_request,
    }


def enrich_tool_result(
    *,
    tool: str,
    payload: dict[str, Any],
    result: dict[str, Any],
    source_text: str = "",
    output_text: str = "",
    provider: str = "",
    model_version: str = "",
) -> dict[str, Any]:
    """Attach provenance, preservation, and review flags without changing core fields."""
    treated = treat_as_clinical_text(source_text)
    report = preservation_report(source_text, output_text or source_text)
    glossary = glossary_lookup(source_text)
    out = dict(result)
    warnings = list(out.get("warnings") or [])
    warnings.extend(report["warnings"])
    if treated["injection_signals"]:
        warnings.append("utterance_injection_signal_ignored")
    if glossary["unknown_terms"]:
        warnings.append("unknown_clinical_terms_marked")
    human_review = bool(
        out.get("human_review_required")
        or report["human_review_required"]
        or treated["injection_signals"]
        or glossary["unknown_terms"]
    )
    out.update(
        {
            "tool": tool,
            "warnings": sorted(set(warnings)),
            "preserved_terms": list(out.get("medical_terms_preserved") or out.get("medical_terms_detected") or []),
            "preserved_numbers": report["source_numbers"],
            "unknown_terms": glossary["unknown_terms"],
            "glossary": glossary,
            "provenance": {
                "provider": provider or str(out.get("source") or "unknown"),
                "model_version": model_version or "",
                "utterance_treated_as": treated["treated_as"],
                "tool_instruction_allowed": False,
            },
            "human_review_required": human_review,
            "clinical_decision_authority": False,
            "safety_class": out.get("safety_class") or "communication_assist",
        }
    )
    if "confidence" not in out and "score" in out:
        out["confidence"] = float(out.get("score") or 0) / 100.0
    return out


def validate_audio_payload(audio_b64: str, mime_type: str, *, max_bytes: int = 4_000_000) -> dict[str, Any]:
    allowed = {
        "audio/webm",
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/ogg",
        "audio/mp4",
        "audio/x-m4a",
    }
    mime = (mime_type or "").split(";")[0].strip().lower()
    errors: list[str] = []
    if mime not in allowed:
        errors.append("mime_not_allowed")
    size = 0
    if audio_b64:
        # Approximate decoded size from base64 length
        size = max(0, (len(audio_b64) * 3) // 4)
        if size > max_bytes:
            errors.append("audio_too_large")
    return {
        "ok": not errors,
        "errors": errors,
        "mime_type": mime,
        "approx_bytes": size,
        "max_bytes": max_bytes,
        "allowed_mime": sorted(allowed),
    }
