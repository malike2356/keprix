"""Intake pool validation and disqualify rules."""

from __future__ import annotations

from typing import Any


class IntakeError(ValueError):
    pass


class IntakeDisqualified(IntakeError):
    def __init__(self, message: str = "You are not eligible for this booking.") -> None:
        super().__init__(message)
        self.message = message


def validate_intake_answers(pool: dict[str, Any], answers: dict[str, Any] | None) -> dict[str, Any]:
    """Validate answers against pool questions; raise IntakeDisqualified when a rule hits."""
    answers = dict(answers or {})
    questions = list(pool.get("questions") or [])
    cleaned: dict[str, Any] = {}

    for question in questions:
        qid = str(question.get("id") or "").strip()
        if not qid:
            continue
        qtype = str(question.get("type") or "text").strip().lower()
        required = bool(question.get("required", True))
        raw = answers.get(qid)
        if raw is None or raw == "" or raw == []:
            if required:
                raise IntakeError(f"missing answer for {qid}")
            continue

        if qtype == "text":
            cleaned[qid] = str(raw).strip()
        elif qtype == "single_select":
            options = [str(o.get("value") if isinstance(o, dict) else o) for o in (question.get("options") or [])]
            value = str(raw)
            if options and value not in options:
                raise IntakeError(f"invalid option for {qid}")
            cleaned[qid] = value
        elif qtype == "multi_select":
            options = [str(o.get("value") if isinstance(o, dict) else o) for o in (question.get("options") or [])]
            values = [str(v) for v in (raw if isinstance(raw, list) else [raw])]
            if options and any(v not in options for v in values):
                raise IntakeError(f"invalid option for {qid}")
            cleaned[qid] = values
        else:
            cleaned[qid] = raw

        disqualify = question.get("disqualify_answers") or []
        if isinstance(disqualify, (str, int, float, bool)):
            disqualify = [disqualify]
        disqualify_norm = {str(x) for x in disqualify}
        check_vals = cleaned[qid] if isinstance(cleaned[qid], list) else [cleaned[qid]]
        if any(str(v) in disqualify_norm for v in check_vals):
            raise IntakeDisqualified(str(question.get("disqualify_message") or IntakeDisqualified().message))

    return cleaned


def intake_required_for_source(source: str) -> bool:
    """Public/API require intake when attached; echo/voice may skip."""
    return source not in {"echo", "voice", "agent"}
