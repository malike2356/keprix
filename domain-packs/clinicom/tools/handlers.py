"""Clinicom sidecar tool handlers.

Handlers return JSON strings for registry.dispatch(). Resolution order:
1. KEPRIX_ML_SERVICE_URL (Keprix ML service) when reachable
2. GEMINI_API_KEY / KEPRIX_GEMINI_API_KEY / GOOGLE_API_KEY for translate/simplify/transcribe
3. Deterministic stubs mirroring the Clinicom local sidecar contract
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

_MEDICAL_TERMS = (
    "pain",
    "fever",
    "blood",
    "breathing",
    "medicine",
    "tablet",
    "cough",
    "wound",
    "headache",
    "nausea",
)

_JARGON = {
    "hypertension": "high blood pressure",
    "myocardial infarction": "heart attack",
    "dyspnea": "shortness of breath",
    "pyrexia": "fever",
    "analgesic": "pain relief medicine",
    "antibiotic": "medicine that fights infection",
}

_GEMINI_MODEL = os.environ.get("CLINICOM_GEMINI_MODEL", "gemini-flash-latest")
_V2_TOOL_SOURCE = "keprix-clinicom-stub"


def _extract_terms(text: str) -> list[str]:
    lowered = text.lower()
    return [term for term in _MEDICAL_TERMS if term in lowered]


def _language_label(code: str) -> str:
    labels = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "pl": "Polish",
        "ur": "Urdu",
        "bn": "Bengali",
        "ar": "Arabic",
        "yo": "Yoruba",
        "pa": "Punjabi",
        "hi": "Hindi",
        "zh": "Chinese",
    }
    return labels.get(code.lower(), code.upper())


def _simplify_text(text: str, target_reading_level: int = 8) -> str:
    simplified = text.strip()
    for jargon, plain in _JARGON.items():
        simplified = re.sub(re.escape(jargon), plain, simplified, flags=re.IGNORECASE)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", simplified) if part.strip()]
    if target_reading_level <= 8 and len(sentences) > 3:
        simplified = " ".join(sentences[:3])
    return simplified


def _estimate_reading_level(text: str) -> dict[str, float]:
    words = re.findall(r"[A-Za-z']+", text)
    sentences = max(1, len(re.findall(r"[.!?]+", text)) or 1)
    syllables = sum(max(1, len(re.findall(r"[aeiouyAEIOUY]+", word))) for word in words)
    if not words:
        return {"flesch_kincaid_grade": float(8), "word_count": 0.0}
    grade = 0.39 * (len(words) / sentences) + 11.8 * (syllables / len(words)) - 15.59
    return {"flesch_kincaid_grade": round(max(3.0, min(12.0, grade)), 1), "word_count": float(len(words))}


def _post_ml(path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    base_url = os.environ.get("KEPRIX_ML_SERVICE_URL", "").rstrip("/")
    if not base_url:
        return None
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data if isinstance(data, dict) else None
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def _gemini_api_key() -> str:
    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("KEPRIX_GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("CLINICOM_GEMINI_API_KEY")
        or ""
    ).strip()


def _gemini_generate(prompt: str, *, parts: list[dict[str, Any]] | None = None) -> str | None:
    api_key = _gemini_api_key()
    if not api_key:
        return None
    body_parts: list[dict[str, Any]] = list(parts or [])
    body_parts.append({"text": prompt})
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent",
        data=json.dumps({"contents": [{"parts": body_parts}]}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None
    candidates = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(candidates, list) or not candidates:
        return None
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    raw_parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(raw_parts, list):
        return None
    texts = [str(part.get("text") or "").strip() for part in raw_parts if isinstance(part, dict)]
    joined = "\n".join(piece for piece in texts if piece).strip()
    return joined or None


def _gemini_generate_json(prompt: str) -> dict[str, Any] | None:
    raw = _gemini_generate(prompt)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return payload if isinstance(payload, dict) else None


def _context_snippet(context: Any, *, limit: int = 280) -> str:
    if not context:
        return ""
    if isinstance(context, dict):
        text = context.get("summary") or context.get("text") or json.dumps(context, ensure_ascii=False)
    else:
        text = str(context)
    text = " ".join(str(text).split())
    return text[:limit]


def clinicom_transcribe_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    audio_b64 = str(args.get("audio") or args.get("audio_b64") or "")
    mime_type = str(args.get("mime_type") or "audio/webm")
    language_hint = args.get("language_hint") or args.get("language") or "en"
    ml = _post_ml(
        "/language/transcribe",
        {
            "audio_b64": audio_b64,
            "mime_type": mime_type,
            "language": language_hint,
        },
    )
    if ml and ml.get("text"):
        return json.dumps(
            {
                "text": ml.get("text"),
                "detected_language": ml.get("language") or language_hint,
                "confidence": ml.get("confidence", 0.9),
                "duration_seconds": ml.get("duration_seconds", 1.0),
                "source": "keprix-ml-service",
            }
        )

    if audio_b64 and _gemini_api_key():
        gemini_text = _gemini_generate(
            (
                "Transcribe this clinical encounter audio. "
                f"Language hint: {_language_label(str(language_hint))}. "
                "Return only the transcript text with no preface."
            ),
            parts=[{"inline_data": {"mime_type": mime_type, "data": audio_b64}}],
        )
        if gemini_text:
            return json.dumps(
                {
                    "text": gemini_text,
                    "detected_language": language_hint,
                    "confidence": 0.86,
                    "duration_seconds": max(1.0, len(gemini_text.split()) / 2),
                    "source": "keprix-gemini",
                }
            )

    sample = ""
    if audio_b64:
        try:
            raw = base64.b64decode(audio_b64.encode("utf-8"))
            sample = raw.decode("utf-8", errors="ignore").strip()
        except Exception:
            sample = ""
    text = sample or "Demo transcription from the Keprix Clinicom sidecar."
    return json.dumps(
        {
            "text": text,
            "detected_language": language_hint,
            "confidence": 0.93,
            "duration_seconds": max(1.0, len(text.split()) / 2),
            "source": "keprix-clinicom-stub",
        }
    )


def clinicom_translate_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    text = str(args.get("text") or "")
    source_language = str(args.get("source_language") or args.get("src_lang") or "en")
    target_language = str(args.get("target_language") or args.get("tgt_lang") or "en")

    ml = _post_ml(
        "/language/translate",
        {
            "text": text,
            "src_lang": source_language,
            "tgt_lang": target_language,
        },
    )
    if ml and ml.get("translated_text"):
        return json.dumps(
            {
                "translated_text": ml.get("translated_text"),
                "source_language": ml.get("src_lang") or source_language,
                "target_language": ml.get("tgt_lang") or target_language,
                "medical_terms_detected": _extract_terms(text),
                "confidence": ml.get("confidence", 0.9),
                "source": "keprix-ml-service",
            }
        )

    if source_language != target_language and text.strip() and _gemini_api_key():
        gemini_text = _gemini_generate(
            (
                "You are a clinical interpreter. Translate the patient/clinician utterance accurately. "
                "Preserve medical meaning. Do not add advice. Return only the translation.\n"
                f"Source language: {_language_label(source_language)} ({source_language})\n"
                f"Target language: {_language_label(target_language)} ({target_language})\n"
                f"Text:\n{text}"
            )
        )
        if gemini_text:
            return json.dumps(
                {
                    "translated_text": gemini_text,
                    "source_language": source_language,
                    "target_language": target_language,
                    "medical_terms_detected": _extract_terms(text),
                    "confidence": 0.88,
                    "source": "keprix-gemini",
                }
            )

    if source_language == target_language:
        translated = text
    else:
        translated = f"[{_language_label(target_language)}] {text}"
    return json.dumps(
        {
            "translated_text": translated,
            "source_language": source_language,
            "target_language": target_language,
            "medical_terms_detected": _extract_terms(text),
            "confidence": 0.9,
            "source": "keprix-clinicom-stub",
        }
    )


def clinicom_simplify_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    text = str(args.get("text") or "")
    target_reading_level = int(args.get("target_reading_level") or 8)

    if text.strip() and _gemini_api_key():
        gemini_text = _gemini_generate(
            (
                "Rewrite this clinical text in plain language for patients. "
                f"Target reading level roughly UK year {target_reading_level}. "
                "Keep clinical meaning. Return only the rewritten text.\n\n"
                f"{text}"
            )
        )
        if gemini_text:
            return json.dumps(
                {
                    "simplified_text": gemini_text,
                    "readability_scores": _estimate_reading_level(gemini_text),
                    "medical_terms_preserved": _extract_terms(text),
                    "confidence": 0.87,
                    "source": "keprix-gemini",
                }
            )

    simplified = _simplify_text(text, target_reading_level)
    return json.dumps(
        {
            "simplified_text": simplified,
            "readability_scores": _estimate_reading_level(simplified),
            "medical_terms_preserved": _extract_terms(text),
            "confidence": 0.88,
            "source": "keprix-clinicom-stub",
        }
    )


def clinicom_speak_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    text = str(args.get("text") or "")
    language = str(args.get("language") or "en")
    voice_id = str(args.get("voice") or args.get("voice_id") or "auto")

    ml = _post_ml(
        "/language/synthesize",
        {
            "text": text,
            "language": language,
            "voice_id": voice_id,
        },
    )
    if ml and ml.get("audio_b64"):
        return json.dumps(
            {
                "audio_base64": ml.get("audio_b64"),
                "format": ml.get("format") or "mp3",
                "duration_seconds": ml.get("duration_seconds", max(1.0, len(text.split()) / 2)),
                "language": language,
                "source": "keprix-ml-service",
            }
        )

    encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    return json.dumps(
        {
            "audio_base64": encoded,
            "format": "mp3",
            "duration_seconds": max(1.0, len(text.split()) / 2),
            "language": language,
            "source": "keprix-clinicom-stub",
        }
    )


def clinicom_cultural_adapt_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    text = str(args.get("text") or "")
    source_language = str(args.get("source_language") or "en")
    target_language = str(args.get("target_language") or "en")
    context = _context_snippet(args.get("session_context") or args.get("context"))
    ml = _post_ml(
        "/clinicom/deep/cultural-adapt",
        {
            "text": text,
            "source_language": source_language,
            "target_language": target_language,
            "context": context,
        },
    )
    if ml:
        ml.setdefault("source", "keprix-ml-service")
        return json.dumps(ml)
    if _gemini_api_key():
        gemini = _gemini_generate_json(
            (
                "Return JSON only with keys cultural_notes, candidate_phrases, rationale, confidence. "
                "You are assisting a clinical interpreter. Preserve meaning and do not add advice. "
                f"Source language: {_language_label(source_language)}. Target language: {_language_label(target_language)}. "
                f"Context: {context or 'general-practice'}. Text: {text}"
            )
        )
        if gemini:
            gemini.setdefault("source", "keprix-gemini")
            return json.dumps(gemini)
    notes = _extract_terms(text) or ["Check the phrasing against the patient's stated preferences."]
    return json.dumps(
        {
            "cultural_notes": notes[:4],
            "candidate_phrases": [text[:120]] if text else [],
            "rationale": "Deterministic continuity response from the Keprix pack.",
            "confidence": 0.74,
            "source": _V2_TOOL_SOURCE,
        }
    )


def clinicom_teachback_score_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    response = str(args.get("patient_response") or "")
    key_points = [str(item) for item in (args.get("key_points") or []) if str(item).strip()]
    context = _context_snippet(args.get("session_context") or args.get("context"))
    ml = _post_ml(
        "/clinicom/deep/teachback-score",
        {"patient_response": response, "key_points": key_points, "context": context},
    )
    if ml:
        ml.setdefault("source", "keprix-ml-service")
        return json.dumps(ml)
    if _gemini_api_key():
        gemini = _gemini_generate_json(
            (
                "Return JSON only with keys score, strengths, gaps, follow_up_question, coaching_tips, confidence. "
                "Score how well the patient response matches the plan. Keep the clinician as author. "
                f"Context: {context or 'general-practice'}. Key points: {key_points}. Response: {response}"
            )
        )
        if gemini:
            gemini.setdefault("source", "keprix-gemini")
            return json.dumps(gemini)
    score = 80 if response.strip() else 0
    gaps = [point for point in key_points if point and point.lower() not in response.lower()]
    if gaps:
        score = max(40, score - min(30, len(gaps) * 6))
    return json.dumps(
        {
            "score": score,
            "strengths": key_points[:2],
            "gaps": gaps[:4],
            "follow_up_question": "Can you tell me the plan back in your own words?",
            "coaching_tips": ["Ask for the medicine name", "Confirm when to seek help", "Repeat the red flags"],
            "confidence": 0.8,
            "source": _V2_TOOL_SOURCE,
        }
    )


def clinicom_safety_triage_assist_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    text = str(args.get("text") or "")
    safety_terms = [str(item) for item in (args.get("safety_terms") or []) if str(item).strip()]
    context = _context_snippet(args.get("session_context") or args.get("context"))
    ml = _post_ml(
        "/clinicom/deep/safety-triage-assist",
        {"text": text, "safety_terms": safety_terms, "context": context},
    )
    if ml:
        ml.setdefault("source", "keprix-ml-service")
        return json.dumps(ml)
    if _gemini_api_key():
        gemini = _gemini_generate_json(
            (
                "Return JSON only with keys urgency, reasons, checklist, confidence. "
                "You are assisting clinical safety triage; never auto-acknowledge or replace a clinician. "
                f"Context: {context or 'general-practice'}. Safety terms: {safety_terms}. Text: {text}"
            )
        )
        if gemini:
            gemini.setdefault("source", "keprix-gemini")
            return json.dumps(gemini)
    return json.dumps(
        {
            "urgency": "high" if safety_terms else "normal",
            "reasons": safety_terms or ["No explicit red-flag terms supplied"],
            "checklist": [
                "Review the safety message",
                "Confirm clinician acknowledgment",
                "Do not auto-file or auto-discharge",
            ],
            "confidence": 0.82,
            "source": _V2_TOOL_SOURCE,
        }
    )


def clinicom_session_digest_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    context = args.get("context") or args.get("session_context") or {}
    recent_messages = context.get("recent_messages") if isinstance(context, dict) else []
    messages = [str(item.get("summary") or item.get("text") or "") for item in recent_messages if isinstance(item, dict)]
    digest = " ".join(text.strip() for text in messages if text.strip()).strip()
    if not digest and isinstance(context, dict):
        digest = _context_snippet(context, limit=280)
    if _gemini_api_key():
        gemini = _gemini_generate_json(
            (
                "Return JSON only with keys digest, summary_points, languages, safety_flags, confidence. "
                "Write a short encounter memory digest for the next clinician turn. "
                f"Context: {json.dumps(context, ensure_ascii=False)[:2400]}"
            )
        )
        if gemini:
            gemini.setdefault("source", "keprix-gemini")
            return json.dumps(gemini)
    return json.dumps(
        {
            "digest": digest[:280] or "No prior encounter summary available.",
            "summary_points": messages[:4],
            "languages": list(context.get("languages") or []) if isinstance(context, dict) else [],
            "safety_flags": list(context.get("safety_flags") or []) if isinstance(context, dict) else [],
            "confidence": 0.76,
            "source": _V2_TOOL_SOURCE,
        }
    )


def clinicom_specialty_simplify_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    text = str(args.get("text") or "")
    specialty_pack_id = str(args.get("specialty_pack_id") or "general")
    target_reading_level = int(args.get("target_reading_level") or 8)
    context = _context_snippet(args.get("session_context") or args.get("context"))
    ml = _post_ml(
        "/clinicom/deep/specialty-simplify",
        {
            "text": text,
            "specialty_pack_id": specialty_pack_id,
            "target_reading_level": target_reading_level,
            "context": context,
        },
    )
    if ml:
        ml.setdefault("source", "keprix-ml-service")
        return json.dumps(ml)
    if _gemini_api_key():
        gemini = _gemini_generate_json(
            (
                "Return JSON only with keys simplified_text, specialty_pack_id, rationale, readability_scores, medical_terms_preserved, confidence. "
                "Rewrite the clinical text for the named specialty without changing meaning. "
                f"Specialty pack: {specialty_pack_id}. Target reading level: {target_reading_level}. Context: {context or 'general-practice'}. Text: {text}"
            )
        )
        if gemini:
            gemini.setdefault("source", "keprix-gemini")
            return json.dumps(gemini)
    simplified = _simplify_text(text, target_reading_level)
    return json.dumps(
        {
            "simplified_text": simplified,
            "specialty_pack_id": specialty_pack_id,
            "rationale": "Deterministic plain-language continuity output.",
            "readability_scores": _estimate_reading_level(simplified),
            "medical_terms_preserved": _extract_terms(text),
            "confidence": 0.82,
            "source": _V2_TOOL_SOURCE,
        }
    )


def clinicom_confidence_explain_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    score = int(args.get("score") or 0)
    provider_sources = args.get("provider_sources") or {}
    pipeline_timing = args.get("pipeline_timing") or {}
    step_status = args.get("step_status") or []
    context = _context_snippet(args.get("context"))
    ml = _post_ml(
        "/clinicom/deep/confidence-explain",
        {
            "score": score,
            "provider_sources": provider_sources,
            "pipeline_timing": pipeline_timing,
            "step_status": step_status,
            "context": context,
        },
    )
    if ml:
        ml.setdefault("source", "keprix-ml-service")
        return json.dumps(ml)
    if _gemini_api_key():
        gemini = _gemini_generate_json(
            (
                "Return JSON only with keys score, explanation, factors, confidence. "
                "Explain pipeline confidence honestly from the provider sources and step timing. "
                f"Context: {context or 'general-practice'}. Score: {score}. Provider sources: {provider_sources}. Step status: {step_status}"
            )
        )
        if gemini:
            gemini.setdefault("source", "keprix-gemini")
            return json.dumps(gemini)
    return json.dumps(
        {
            "score": score,
            "explanation": "Confidence is estimated from the current pipeline sources and step timing.",
            "factors": [
                "Provider source availability",
                "Latency profile",
                "Degradation status",
            ],
            "confidence": 0.7,
            "source": _V2_TOOL_SOURCE,
        }
    )


def clinicom_specialty_simplify_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    text = str(args.get("text") or "")
    specialty_pack_id = str(args.get("specialty_pack_id") or "general")
    target_reading_level = int(args.get("target_reading_level") or 8)
    context = _context_snippet(args.get("session_context") or args.get("context"))
    ml = _post_ml(
        "/clinicom/deep/specialty-simplify",
        {
            "text": text,
            "specialty_pack_id": specialty_pack_id,
            "target_reading_level": target_reading_level,
            "context": context,
        },
    )
    if ml:
        ml.setdefault("source", "keprix-ml-service")
        return json.dumps(ml)
    if _gemini_api_key():
        gemini = _gemini_generate_json(
            (
                "Return JSON only with keys simplified_text, rationale, readability_scores, medical_terms_preserved, confidence. "
                "Rewrite the text in plain language for the specified specialty pack. "
                f"Specialty pack: {specialty_pack_id}. Reading level: {target_reading_level}. Text: {text}"
            )
        )
        if gemini:
            gemini.setdefault("source", "keprix-gemini")
            return json.dumps(gemini)
    simplified = _simplify_text(text, target_reading_level)
    return json.dumps(
        {
            "simplified_text": simplified,
            "specialty_pack_id": specialty_pack_id,
            "rationale": "Deterministic plain-language continuity output.",
            "readability_scores": _estimate_reading_level(simplified),
            "medical_terms_preserved": _extract_terms(text),
            "confidence": 0.82,
            "source": _V2_TOOL_SOURCE,
        }
    )


def clinicom_product_help_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    question = str(args.get("question") or "").strip()
    grounding = str(args.get("grounding_corpus") or "").strip()[:14000]
    capabilities = str(args.get("capabilities_summary") or "").strip()[:2400]
    if not question:
        return json.dumps(
            {
                "answer": "Ask a Clinicom product question.",
                "grounded": False,
                "confidence": 0,
                "mode": "refuse",
                "source": _V2_TOOL_SOURCE,
            }
        )
    if _gemini_api_key():
        gemini = _gemini_generate_json(
            (
                "Return JSON only with keys answer (string), grounded (boolean), confidence (number 0-1), mode (string). "
                "You are Ask Clinicom product help for Clinicom AI (Healthcare Communication Intelligence). "
                "Use ONLY the grounding corpus and capabilities summary. "
                "Explain Clinicom surfaces, interpreter vs dashboard, roles, sidecar tools, pricing location, "
                "trust posture, and how deep AI tools support clinicians. "
                "Not medical advice. Do not invent live user counts, revenue, certifications, or URLs missing from grounding. "
                "If grounding is insufficient, set grounded=false, mode=refuse, answer exactly INSUFFICIENT_GROUNDING. "
                f"Question: {question}\n"
                f"Capabilities summary: {capabilities or 'unavailable'}\n"
                f"Grounding corpus:\n{grounding or '(empty)'}"
            )
        )
        if gemini:
            answer = str(gemini.get("answer") or "").strip()
            grounded = bool(gemini.get("grounded")) and bool(answer) and answer.upper() != "INSUFFICIENT_GROUNDING"
            return json.dumps(
                {
                    "answer": answer or "INSUFFICIENT_GROUNDING",
                    "grounded": grounded,
                    "confidence": float(gemini.get("confidence") or (0.7 if grounded else 0)),
                    "mode": (str(gemini.get("mode") or "sidecar") if grounded else "refuse"),
                    "source": "keprix-gemini",
                }
            )
    if grounding:
        primary_match = re.search(
            r"Primary grounded answer:\s*(.*?)(?:\n\nFAQ|\n\nDOC|$)",
            grounding,
            flags=re.I | re.S,
        )
        if primary_match and primary_match.group(1).strip():
            return json.dumps(
                {
                    "answer": primary_match.group(1).strip()[:1200],
                    "grounded": True,
                    "confidence": 0.7,
                    "mode": "docs",
                    "source": _V2_TOOL_SOURCE,
                }
            )
        excerpt = re.sub(r"\s+", " ", grounding).strip()[:420]
        return json.dumps(
            {
                "answer": excerpt,
                "grounded": True,
                "confidence": 0.55,
                "mode": "docs",
                "source": _V2_TOOL_SOURCE,
            }
        )
    return json.dumps(
        {
            "answer": "INSUFFICIENT_GROUNDING",
            "grounded": False,
            "confidence": 0,
            "mode": "refuse",
            "source": _V2_TOOL_SOURCE,
        }
    )
