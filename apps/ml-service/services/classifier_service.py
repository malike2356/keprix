from __future__ import annotations

import asyncio
import json
from collections import Counter
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

INTENT_RULES: dict[str, list[str]] = {
    "quote_request": ["quote", "how much", "price", "cost", "rate", "how many"],
    "report_submission": ["finished", "completed", "water found", "depth reached", "log", "report"],
    "dues_inquiry": ["dues", "payment", "paid", "expire", "subscription", "fee"],
    "member_lookup": ["is", "registered", "check", "find member", "lookup"],
    "wrc_licence": ["licence", "license", "wrc", "code", "register drilling"],
    "complaint": ["complaint", "problem", "issue", "bad practice", "violated", "fraud"],
    "greeting": ["hello", "hi", "good morning", "good afternoon", "greetings"],
}

FORMATION_KEYWORDS: dict[str, list[str]] = {
    "laterite": ["laterite", "red", "ferruginous", "ironstone", "concretionary"],
    "saprolite": ["saprolite", "decomposed", "weathered granite", "weathered gneiss", "regolith"],
    "fresh_basement": ["fresh granite", "fresh gneiss", "schist", "basement", "quartzite", "crystalline"],
    "shale": ["shale", "mudstone", "argillite"],
    "sandstone": ["sandstone", "sand", "gravel", "sandy"],
    "alluvium": ["alluvium", "alluvial", "gravel", "silt", "flood plain"],
    "clay": ["clay", "clayey", "plastic", "grey clay", "brown clay"],
}

FORMATION_YIELD_PRIOR: dict[str, str] = {
    "laterite": "dry",
    "saprolite": "marginal",
    "fresh_basement": "marginal",
    "shale": "dry",
    "sandstone": "community",
    "alluvium": "community",
    "clay": "dry",
    "unknown": "marginal",
}


@dataclass
class DuplicateCandidate:
    member_id: str
    full_name: str
    phone: str
    similarity_score: float
    match_reason: str


@dataclass
class AnomalyScore:
    agent_id: str
    anomaly_score: float
    is_anomalous: bool
    similar_past_sequences: list[str]
    explanation: str


def classify_intent_rules(text: str) -> tuple[str, float]:
    lower = text.lower()
    scores: dict[str, float] = {}
    for intent, keywords in INTENT_RULES.items():
        hits = sum(1 for keyword in keywords if keyword in lower)
        if hits:
            scores[intent] = hits / len(keywords)
    if not scores:
        return "general_inquiry", 0.4
    top = max(scores, key=scores.get)
    return top, min(0.9, scores[top] * 2)


def classify_formation_rules(description: str) -> tuple[str, float]:
    lower = description.lower()
    scores: dict[str, int] = {}
    for label, keywords in FORMATION_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in lower)
        if hits:
            scores[label] = hits
    if not scores:
        return "unknown", 0.0
    top = max(scores, key=scores.get)
    return top, min(0.85, 0.5 + scores[top] * 0.15)


def predict_yield_rules(formation: str, depth_m: float) -> tuple[str, float]:
    result = FORMATION_YIELD_PRIOR.get(formation, "marginal")
    if formation == "fresh_basement" and depth_m > 60:
        result = "domestic"
    return result, 0.45


def fuzzy_name_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left.lower(), right.lower()).ratio()


def check_duplicate_rules(
    first_name: str,
    last_name: str,
    phone: str | None,
    dob: str | None,
    existing_members: list[dict[str, Any]],
) -> list[DuplicateCandidate]:
    full_name = f"{first_name} {last_name}".strip()
    candidates: list[DuplicateCandidate] = []
    for member in existing_members:
        member_full = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
        name_similarity = fuzzy_name_similarity(full_name, member_full)
        reasons: list[str] = []
        if name_similarity >= 0.85:
            reasons.append(f"name similarity {name_similarity:.0%}")
        if phone and member.get("phone") and phone[-8:] == str(member["phone"])[-8:]:
            reasons.append("phone number match")
        if dob and member.get("dob") and dob == member["dob"]:
            reasons.append("date of birth match")
        if not reasons:
            continue
        score = name_similarity * 0.5
        if any("phone" in reason for reason in reasons):
            score += 0.3
        if any("birth" in reason for reason in reasons):
            score += 0.2
        candidates.append(
            DuplicateCandidate(
                member_id=str(member.get("member_number") or member.get("member_id") or ""),
                full_name=member_full,
                phone=str(member.get("phone") or ""),
                similarity_score=min(1.0, score),
                match_reason=", ".join(reasons),
            )
        )
    return sorted(candidates, key=lambda candidate: candidate.similarity_score, reverse=True)[:5]


class ClassifierService:
    def __init__(self, db_pool: Any | None = None, model_dir: str | Path = "models/classifiers"):
        self._pool = db_pool
        self._model_dir = Path(model_dir)
        self._intent_model = None
        self._formation_model = None
        self._yield_model = None
        self._agent_playbooks: dict[str, Counter[tuple[str, str]]] = {}
        self._load_models()

    def _load_models(self) -> None:
        try:
            import joblib
        except Exception:
            return
        for filename, attr in [
            ("intent_v1.joblib", "_intent_model"),
            ("formation_v1.joblib", "_formation_model"),
            ("yield_v1.joblib", "_yield_model"),
        ]:
            path = self._model_dir / filename
            if path.exists():
                setattr(self, attr, joblib.load(path))

    def reload_models(self) -> dict[str, bool]:
        self._load_models()
        return {
            "intent": self._intent_model is not None,
            "formation": self._formation_model is not None,
            "yield": self._yield_model is not None,
        }

    def classify_intent(self, text: str, context: str | None = None) -> dict[str, Any]:
        full_text = f"{context}\n{text}" if context else text
        if self._intent_model is not None:
            probabilities = self._intent_model.predict_proba([full_text])[0]
            classes = self._intent_model.classes_
            top_index = probabilities.argmax()
            prediction, confidence, model = str(classes[top_index]), float(probabilities[top_index]), "ml"
        else:
            prediction, confidence = classify_intent_rules(full_text)
            model = "rules"
        self._log_prediction("intent", {"text": text, "context": context}, prediction, confidence, model)
        return {"intent": prediction, "confidence": confidence, "model": model}

    def classify_formation(self, description: str) -> dict[str, Any]:
        if self._formation_model is not None:
            prediction = str(self._formation_model.predict([description])[0])
            confidence = float(self._formation_model.predict_proba([description]).max())
            model = "ml"
        else:
            prediction, confidence = classify_formation_rules(description)
            model = "rules"
        self._log_prediction("formation", {"description": description}, prediction, confidence, model)
        return {"formation": prediction, "confidence": confidence, "model": model}

    def predict_yield(self, formation: str, depth_m: float, **kwargs: Any) -> dict[str, Any]:
        if self._yield_model is not None:
            features = [formation, depth_m, kwargs.get("gps_lat") or 0.0, kwargs.get("gps_lng") or 0.0]
            prediction = str(self._yield_model.predict([features])[0])
            confidence = float(self._yield_model.predict_proba([features]).max())
            model = "ml"
        else:
            prediction, confidence = predict_yield_rules(formation, depth_m)
            model = "rules"
        self._log_prediction("yield", {"formation": formation, "depth_m": depth_m, **kwargs}, prediction, confidence, model)
        return {"yield_class": prediction, "confidence": confidence, "model": model}

    def check_duplicate(
        self,
        first_name: str,
        last_name: str,
        phone: str | None = None,
        dob: str | None = None,
        existing_members: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        candidates = check_duplicate_rules(first_name, last_name, phone, dob, existing_members or [])
        prediction = "duplicate" if candidates and candidates[0].similarity_score >= 0.75 else "unique"
        confidence = candidates[0].similarity_score if candidates else 0.0
        self._log_prediction(
            "duplicate",
            {"first_name": first_name, "last_name": last_name, "phone": phone, "dob": dob},
            prediction,
            confidence,
            "rules",
        )
        return {
            "is_likely_duplicate": prediction == "duplicate",
            "candidates": [asdict(candidate) for candidate in candidates],
        }

    def load_playbook(self, agent_id: str, action_sequences: list[list[str]]) -> None:
        bigrams: Counter[tuple[str, str]] = Counter()
        for sequence in action_sequences:
            for left, right in zip(sequence, sequence[1:]):
                bigrams[(left, right)] += 1
        self._agent_playbooks[agent_id] = bigrams

    def detect_anomaly(self, agent_id: str, action_sequence: list[str]) -> dict[str, Any]:
        playbook = self._agent_playbooks.get(agent_id, Counter())
        if not playbook:
            result = AnomalyScore(agent_id, 0.0, False, [], "No playbook history. Action permitted.")
            return asdict(result)
        bigrams = [(action_sequence[index], action_sequence[index + 1]) for index in range(len(action_sequence) - 1)]
        if not bigrams:
            result = AnomalyScore(agent_id, 0.0, False, [], "Single action; no sequence to score.")
            return asdict(result)
        unseen = sum(1 for bigram in bigrams if playbook[bigram] == 0)
        score = unseen / len(bigrams)
        result = AnomalyScore(
            agent_id=agent_id,
            anomaly_score=score,
            is_anomalous=score > 0.85,
            similar_past_sequences=[],
            explanation=f"{unseen}/{len(bigrams)} action transitions not seen in playbook.",
        )
        return asdict(result)

    async def label_training_record(self, log_id: str, label: str, labeled_by: str) -> None:
        if self._pool is None:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE ml_training_log
                SET label=$2, labeled_by=$3, labeled_at=now()
                WHERE id=$1
                """,
                log_id,
                label,
                labeled_by,
            )

    async def get_unlabeled(self, classifier: str, limit: int = 50) -> list[dict[str, Any]]:
        if self._pool is None:
            return []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, classifier, input_json, prediction, confidence, model_type, created_at
                FROM ml_training_log
                WHERE classifier=$1 AND label IS NULL
                ORDER BY created_at ASC
                LIMIT $2
                """,
                classifier,
                limit,
            )
        return [dict(row) for row in rows]

    def _log_prediction(
        self,
        classifier: str,
        input_data: dict[str, Any],
        prediction: str,
        confidence: float,
        model_type: str,
    ) -> None:
        if self._pool is None:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._write_log(classifier, input_data, prediction, confidence, model_type))
        except RuntimeError:
            pass

    async def _write_log(
        self,
        classifier: str,
        input_data: dict[str, Any],
        prediction: str,
        confidence: float,
        model_type: str,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ml_training_log (classifier, input_json, prediction, confidence, model_type)
                VALUES ($1, $2::jsonb, $3, $4, $5)
                """,
                classifier,
                json.dumps(input_data),
                prediction,
                confidence,
                model_type,
            )
