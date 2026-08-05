# keprix ML: Domain Classifiers and Predictors (Prompt 232)

**Series:** ML infrastructure (229-232). Builds on scaffold from 229. Requires production data; stubs are active from day one, classifiers gain accuracy as data accumulates.
**Platform:** keprix agent OS kernel
**Phase:** Phase 3 (classifiers ship with rule-based stubs; ML models trained when labeled data is available)
**Principle:** Each classifier exposes the same tool interface from day one. The implementation behind the interface upgrades from rules to ML without any agent code changing.

---

## 1. What this prompt builds

- Intent classifier: routes incoming messages to the correct ABBIS sub-agent
- Geological formation classifier: labels formation entries in drilling logs
- Borehole yield predictor: estimates water yield range from drilling parameters
- Duplicate member detector: fuzzy match + embedding similarity to catch re-registrations
- Agent anomaly detector: scores action sequences for deviation from trained playbooks
- Training data collection pipeline: every inference writes a record that can be labeled and used for retraining
- Model versioning and hot-swap: load new model without restarting the service

---

## 2. Architecture: stub-to-ML upgrade path

Every classifier follows this upgrade path:

```
Phase 3a (stub): Rule-based classifier with explicit keyword lists and heuristics.
                 Ships on day one. Records every input to the training log.

Phase 3b (first ML): scikit-learn classifier trained on labeled training data.
                     Swapped in via model versioning when labeling is complete.

Phase 3c (production ML): Retrained monthly with new labeled data; evaluated
                          against previous version before promotion.
```

The `ClassifierService` loads the active model version from disk. Deploying a new model is: place new file, call the reload endpoint. No service restart needed.

---

## 3. Intent classifier

### 3.1 Intents (ABBIS WhatsApp use case)

| Intent | Description | Example trigger phrase |
|---|---|---|
| `quote_request` | Member wants a borehole drilling quote | "how much to drill at Tema" |
| `report_submission` | Submitting a drilling log or progress update | "I finished the job, water found at 42m" |
| `dues_inquiry` | Question about membership dues | "when is my payment due" |
| `member_lookup` | Looking up a member or company | "is Kari Boreholes registered" |
| `wrc_licence` | WRC licence code request or status | "I need my licence code" |
| `complaint` | Complaint about a member or practice | "they drilled without following standards" |
| `general_inquiry` | General question not covered above | (catch-all) |
| `greeting` | Casual opener with no clear intent | "hello", "good morning" |

### 3.2 Rule-based stub (Phase 3a)

```python
INTENT_RULES: dict[str, list[str]] = {
    "quote_request": ["quote", "how much", "price", "cost", "rate", "how many"],
    "report_submission": ["finished", "completed", "water found", "depth reached", "log", "report"],
    "dues_inquiry": ["dues", "payment", "paid", "expire", "subscription", "fee"],
    "member_lookup": ["is", "registered", "check", "find member", "lookup"],
    "wrc_licence": ["licence", "license", "wrc", "code", "register drilling"],
    "complaint": ["complaint", "problem", "issue", "bad practice", "violated", "fraud"],
    "greeting": ["hello", "hi", "good morning", "good afternoon", "greetings"],
}

def classify_intent_rules(text: str) -> tuple[str, float]:
    lower = text.lower()
    scores = {}
    for intent, keywords in INTENT_RULES.items():
        hit_count = sum(1 for kw in keywords if kw in lower)
        if hit_count:
            scores[intent] = hit_count / len(keywords)
    if not scores:
        return "general_inquiry", 0.4
    top = max(scores, key=scores.get)
    return top, min(0.9, scores[top] * 2)  # scale up; cap at 0.9 for stubs
```

### 3.3 ML model (Phase 3b)

When `models/classifiers/intent_v1.joblib` exists, load it at startup and route through ML:

```python
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

def train_intent_classifier(training_data: list[dict]) -> Pipeline:
    """
    training_data: [{"text": "...", "intent": "quote_request"}, ...]
    """
    texts = [d["text"] for d in training_data]
    labels = [d["intent"] for d in training_data]
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
        ("clf", LogisticRegression(max_iter=1000, C=1.0)),
    ])
    pipeline.fit(texts, labels)
    return pipeline

def classify_intent_ml(pipeline: Pipeline, text: str) -> tuple[str, float]:
    probs = pipeline.predict_proba([text])[0]
    classes = pipeline.classes_
    top_idx = probs.argmax()
    return classes[top_idx], float(probs[top_idx])
```

---

## 4. Geological formation classifier

### 4.1 Formation classes

| Label | Description |
|---|---|
| `laterite` | Weathered surface layer; reddish-brown; poor aquifer |
| `saprolite` | Partially weathered basement; moderate permeability |
| `fresh_basement` | Granite/gneiss/schist; requires fracture zones for yield |
| `shale` | Confining layer; poor aquifer; note presence |
| `sandstone` | Sedimentary aquifer; moderate-high yield |
| `alluvium` | Unconsolidated sediment; high yield near rivers |
| `clay` | Low permeability; aquiclude |
| `unknown` | Description insufficient to classify |

### 4.2 Rule-based stub

```python
FORMATION_KEYWORDS: dict[str, list[str]] = {
    "laterite": ["laterite", "red", "ferruginous", "ironstone", "concretionary"],
    "saprolite": ["saprolite", "decomposed", "weathered granite", "weathered gneiss", "regolith"],
    "fresh_basement": ["fresh granite", "fresh gneiss", "schist", "basement", "quartzite", "crystalline"],
    "shale": ["shale", "mudstone", "argillite"],
    "sandstone": ["sandstone", "sand", "gravel", "sandy"],
    "alluvium": ["alluvium", "alluvial", "gravel", "silt", "flood plain"],
    "clay": ["clay", "clayey", "plastic", "grey clay", "brown clay"],
}

def classify_formation_rules(description: str) -> tuple[str, float]:
    lower = description.lower()
    scores = {}
    for label, kws in FORMATION_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in lower)
        if hits:
            scores[label] = hits
    if not scores:
        return "unknown", 0.0
    top = max(scores, key=scores.get)
    return top, min(0.85, 0.5 + scores[top] * 0.15)
```

### 4.3 ML upgrade path

Same as intent: store labeled formation descriptions in training log. When 500+ labeled examples exist, train a TF-IDF + logistic regression model and save as `models/classifiers/formation_v1.joblib`.

---

## 5. Borehole yield predictor

### 5.1 Output classes (not a regression problem at MVP)

| Label | Yield range (L/min) |
|---|---|
| `dry` | 0 |
| `marginal` | 1 to 5 |
| `domestic` | 6 to 20 |
| `community` | 21 to 60 |
| `industrial` | Over 60 |

### 5.2 Input features

| Feature | Type | Source |
|---|---|---|
| `formation` | categorical | formation classifier output |
| `depth_m` | float | total drilled depth |
| `first_water_m` | float | first water strike depth (optional) |
| `gps_lat` | float | GPS latitude (optional) |
| `gps_lng` | float | GPS longitude (optional) |
| `region` | categorical | ABBIS zone (e.g. "Greater Accra") |

### 5.3 Rule-based stub

```python
FORMATION_YIELD_PRIOR: dict[str, str] = {
    "laterite": "dry",
    "saprolite": "marginal",
    "fresh_basement": "marginal",  # fracture zones upgrade this
    "shale": "dry",
    "sandstone": "community",
    "alluvium": "community",
    "clay": "dry",
    "unknown": "marginal",
}

def predict_yield_rules(formation: str, depth_m: float) -> tuple[str, float]:
    base = FORMATION_YIELD_PRIOR.get(formation, "marginal")
    # Depth heuristic: deeper fracture zones often hit better yield in basement
    if formation == "fresh_basement" and depth_m > 60:
        base = "domestic"
    return base, 0.45  # low confidence; flag as rule-based to user
```

### 5.4 ML upgrade path

When drilling log data accumulates in the ABBIS database (target: 200 completed logs with known water yield), train a `RandomForestClassifier` on formation + depth + location features. Store as `models/classifiers/yield_v1.joblib`. Geographic clustering (lat/lng) is critical; add KMeans cluster feature at training time.

---

## 6. Duplicate member detector

### 6.1 Why this is needed

Members may attempt to register twice under slightly different names, different phone numbers, or with a national ID typo. The duplicate detector runs before admin approval and surfaces likely duplicates for review.

### 6.2 Phase 3a: fuzzy matching

```python
from difflib import SequenceMatcher
from dataclasses import dataclass

@dataclass
class DuplicateCandidate:
    member_id: str
    full_name: str
    phone: str
    similarity_score: float
    match_reason: str

def fuzzy_name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def check_duplicate_rules(
    first_name: str,
    last_name: str,
    phone: str | None,
    dob: str | None,
    existing_members: list[dict],
) -> list[DuplicateCandidate]:
    candidates = []
    full_name = f"{first_name} {last_name}".strip()
    for m in existing_members:
        m_full = f"{m['first_name']} {m['last_name']}".strip()
        name_sim = fuzzy_name_similarity(full_name, m_full)

        reasons = []
        if name_sim >= 0.85:
            reasons.append(f"name similarity {name_sim:.0%}")
        if phone and m.get("phone") and phone[-8:] == m["phone"][-8:]:
            reasons.append("phone number match")
        if dob and m.get("dob") and dob == m["dob"]:
            reasons.append("date of birth match")

        if reasons:
            score = name_sim * 0.5 + (0.3 if "phone" in str(reasons) else 0) + (0.2 if "birth" in str(reasons) else 0)
            candidates.append(DuplicateCandidate(
                member_id=m["member_number"],
                full_name=m_full,
                phone=m.get("phone", ""),
                similarity_score=min(1.0, score),
                match_reason=", ".join(reasons),
            ))

    return sorted(candidates, key=lambda c: c.similarity_score, reverse=True)[:5]
```

### 6.3 Phase 3b: embedding similarity

When 500+ members exist, supplement fuzzy matching with embedding-based dedup:

1. Embed the candidate's full name + dob + phone last-4 as a single string
2. Query the `member-identities` knowledge pack (a special embedding pack seeded with all existing member identity strings)
3. Any result with cosine similarity > 0.92 is surfaced as a duplicate candidate
4. The pack is updated each time a new member is approved

Add `member-identities` as a special pack in the `knowledge_packs` table (prompt 230 infrastructure). Ingest format: `"{first_name} {last_name} {dob} {phone_last4}"` per member.

---

## 7. Agent anomaly detector

### 7.1 Purpose

The keprix mutation engine (prompt 28) executes irreversible agent actions (data writes, external messages, financial records). Before executing, the engine optionally calls `detect_agent_anomaly` to score whether the action sequence is typical for this agent's playbook.

### 7.2 Input and output

```python
@dataclass
class AnomalyScore:
    agent_id: str
    anomaly_score: float     # 0.0 = fully expected, 1.0 = never seen before
    is_anomalous: bool       # True if score > threshold (default 0.85)
    similar_past_sequences: list[str]
    explanation: str
```

### 7.3 Phase 3a: n-gram action fingerprint

```python
from collections import Counter

# Loaded from database: historical action sequences per agent_id
_agent_playbooks: dict[str, Counter] = {}

def load_playbook(agent_id: str, action_sequences: list[list[str]]) -> None:
    bigrams = Counter()
    for seq in action_sequences:
        for a, b in zip(seq, seq[1:]):
            bigrams[(a, b)] += 1
    _agent_playbooks[agent_id] = bigrams

def score_anomaly(agent_id: str, action_sequence: list[str]) -> AnomalyScore:
    playbook = _agent_playbooks.get(agent_id, Counter())
    if not playbook:
        # No history: new agent, cannot score
        return AnomalyScore(
            agent_id=agent_id,
            anomaly_score=0.0,
            is_anomalous=False,
            similar_past_sequences=[],
            explanation="No playbook history. Action permitted.",
        )

    bigrams = [(action_sequence[i], action_sequence[i+1]) for i in range(len(action_sequence)-1)]
    if not bigrams:
        return AnomalyScore(agent_id=agent_id, anomaly_score=0.0, is_anomalous=False,
                            similar_past_sequences=[], explanation="Single action; no sequence to score.")

    unseen = sum(1 for bg in bigrams if playbook[bg] == 0)
    anomaly_score = unseen / len(bigrams)

    return AnomalyScore(
        agent_id=agent_id,
        anomaly_score=anomaly_score,
        is_anomalous=anomaly_score > 0.85,
        similar_past_sequences=[],  # populated in Phase 3b
        explanation=f"{unseen}/{len(bigrams)} action transitions not seen in playbook.",
    )
```

### 7.4 Phase 3b: embedding-based sequence matching

Encode the action sequence as a sentence (`"ACTION_A then ACTION_B then ACTION_C"`) and embed it using the embedding service. Query the `agent-playbooks` knowledge pack for the most similar historical sequences. If the best match has cosine similarity < 0.7, flag as anomalous.

---

## 8. Classifier service (services/classifier_service.py)

```python
from dataclasses import dataclass, asdict
from pathlib import Path
import joblib

from ..utils.errors import ClassifierNotTrainedError
from .embedding_service import EmbeddingService

CLASSIFIERS_DIR = Path("models/classifiers")

class ClassifierService:
    def __init__(self, embedding_svc: EmbeddingService | None = None):
        self._intent_model = None
        self._formation_model = None
        self._yield_model = None
        self._embedding_svc = embedding_svc
        self._load_models()

    def _load_models(self) -> None:
        for name, attr in [
            ("intent_v1.joblib", "_intent_model"),
            ("formation_v1.joblib", "_formation_model"),
            ("yield_v1.joblib", "_yield_model"),
        ]:
            path = CLASSIFIERS_DIR / name
            if path.exists():
                setattr(self, attr, joblib.load(path))

    def reload_models(self) -> dict:
        """Hot-swap: reload all models from disk without restart."""
        self._load_models()
        return {
            "intent": self._intent_model is not None,
            "formation": self._formation_model is not None,
            "yield": self._yield_model is not None,
        }

    def classify_intent(self, text: str, context: str | None = None) -> dict:
        full_text = f"{context}\n{text}" if context else text
        if self._intent_model:
            intent, confidence = classify_intent_ml(self._intent_model, full_text)
        else:
            intent, confidence = classify_intent_rules(full_text)
        return {
            "intent": intent,
            "confidence": confidence,
            "model": "ml" if self._intent_model else "rules",
        }

    def classify_formation(self, description: str) -> dict:
        if self._formation_model:
            label = self._formation_model.predict([description])[0]
            prob = self._formation_model.predict_proba([description]).max()
        else:
            label, prob = classify_formation_rules(description)
        return {
            "formation": label,
            "confidence": float(prob),
            "model": "ml" if self._formation_model else "rules",
        }

    def predict_yield(self, formation: str, depth_m: float, **kwargs) -> dict:
        if self._yield_model:
            features = self._build_yield_features(formation, depth_m, **kwargs)
            label = self._yield_model.predict([features])[0]
            prob = self._yield_model.predict_proba([features]).max()
        else:
            label, prob = predict_yield_rules(formation, depth_m)
        return {
            "yield_class": label,
            "confidence": float(prob),
            "model": "ml" if self._yield_model else "rules",
        }

    def _build_yield_features(self, formation: str, depth_m: float, **kwargs) -> list:
        from sklearn.preprocessing import LabelEncoder
        # This must match the feature order used at training time
        # Store the feature spec in models/classifiers/yield_feature_spec.json
        return [formation, depth_m, kwargs.get("gps_lat", 0.0), kwargs.get("gps_lng", 0.0)]

    def check_duplicate(self, first_name: str, last_name: str, phone: str | None, dob: str | None, existing: list[dict]) -> dict:
        candidates = check_duplicate_rules(first_name, last_name, phone, dob, existing)
        return {
            "is_likely_duplicate": len(candidates) > 0 and candidates[0].similarity_score >= 0.75,
            "candidates": [asdict(c) for c in candidates],
        }

    def detect_anomaly(self, agent_id: str, action_sequence: list[str]) -> dict:
        result = score_anomaly(agent_id, action_sequence)
        return asdict(result)
```

---

## 9. Classifiers router (routers/classifiers.py)

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..services.classifier_service import ClassifierService
from ..dependencies import get_classifier_service

router = APIRouter()

class IntentRequest(BaseModel):
    text: str
    context: str | None = None

class FormationRequest(BaseModel):
    description: str

class YieldRequest(BaseModel):
    formation: str
    depth_m: float
    gps_lat: float | None = None
    gps_lng: float | None = None

class DuplicateRequest(BaseModel):
    first_name: str
    last_name: str
    phone: str | None = None
    dob: str | None = None
    existing_members: list[dict] = []

class AnomalyRequest(BaseModel):
    agent_id: str
    action_sequence: list[str]

@router.post("/intent")
async def classify_intent(req: IntentRequest, svc: ClassifierService = Depends(get_classifier_service)):
    return svc.classify_intent(req.text, req.context)

@router.post("/formation")
async def classify_formation(req: FormationRequest, svc: ClassifierService = Depends(get_classifier_service)):
    return svc.classify_formation(req.description)

@router.post("/yield")
async def predict_yield(req: YieldRequest, svc: ClassifierService = Depends(get_classifier_service)):
    return svc.predict_yield(req.formation, req.depth_m, gps_lat=req.gps_lat, gps_lng=req.gps_lng)

@router.post("/duplicate")
async def check_duplicate(req: DuplicateRequest, svc: ClassifierService = Depends(get_classifier_service)):
    return svc.check_duplicate(req.first_name, req.last_name, req.phone, req.dob, req.existing_members)

@router.post("/anomaly")
async def detect_anomaly(req: AnomalyRequest, svc: ClassifierService = Depends(get_classifier_service)):
    return svc.detect_anomaly(req.agent_id, req.action_sequence)

@router.post("/reload")
async def reload_models(svc: ClassifierService = Depends(get_classifier_service)):
    return svc.reload_models()
```

---

## 10. Training data collection pipeline

Every classifier inference must write a training record. This is how the training dataset grows without extra manual effort.

### 10.1 Database schema

Add to the ML service database (migration `0006_training_log.sql`):

```sql
CREATE TABLE ml_training_log (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  classifier  TEXT NOT NULL,           -- "intent", "formation", "yield", "duplicate"
  input_json  JSONB NOT NULL,
  prediction  TEXT NOT NULL,
  confidence  FLOAT NOT NULL,
  model_type  TEXT NOT NULL,           -- "rules" or "ml"
  label       TEXT,                    -- NULL until human-labeled
  labeled_at  TIMESTAMPTZ,
  labeled_by  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ml_training_log_classifier_idx ON ml_training_log(classifier, label);
CREATE INDEX ml_training_log_unlabeled_idx ON ml_training_log(classifier) WHERE label IS NULL;
```

### 10.2 Logging in the service

Wrap every classifier call:

```python
async def _log_prediction(
    self,
    classifier: str,
    input_data: dict,
    prediction: str,
    confidence: float,
    model_type: str,
):
    # Fire and forget; do not block the response
    asyncio.create_task(self._write_log(classifier, input_data, prediction, confidence, model_type))

async def _write_log(self, classifier, input_data, prediction, confidence, model_type):
    async with self._pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO ml_training_log (classifier, input_json, prediction, confidence, model_type)
            VALUES ($1, $2, $3, $4, $5)
            """,
            classifier, json.dumps(input_data), prediction, confidence, model_type,
        )
```

### 10.3 Labeling API

Add to classifiers router:

```python
class LabelRequest(BaseModel):
    log_id: str
    label: str
    labeled_by: str

@router.patch("/training-log/{log_id}/label")
async def label_training_record(log_id: str, req: LabelRequest, svc: ClassifierService = Depends(get_classifier_service)):
    await svc.label_training_record(log_id, req.label, req.labeled_by)
    return {"log_id": log_id, "label": req.label}

@router.get("/training-log/{classifier}/unlabeled")
async def get_unlabeled(classifier: str, limit: int = 50, svc: ClassifierService = Depends(get_classifier_service)):
    return await svc.get_unlabeled(classifier, limit)
```

Labeling UI: a simple admin page in ABBIS at `/admin/ml/label` that shows unlabeled records one at a time and lets the admin click the correct label. This is the cheapest path to a training dataset.

---

## 11. Model training commands

Create `apps/ml-service/train/` directory:

`train/train_intent.py` - loads labeled records from `ml_training_log` where `classifier='intent'` and `label IS NOT NULL`, trains the pipeline, saves to `models/classifiers/intent_v1.joblib`. Prints precision/recall per class. Minimum 50 labeled examples required per class before training.

`train/train_formation.py` - same structure for formation classifier. Minimum 30 examples per formation class.

`train/train_yield.py` - trains yield predictor. Uses GPS coordinates as features; requires a feature scaler saved alongside the model as `yield_v1_scaler.joblib`.

Run training:
```bash
cd apps/ml-service
python -m train.train_intent --min-per-class 50
python -m train.train_formation --min-per-class 30
python -m train.train_yield --min-samples 200
# After training, hot-swap:
curl -X POST http://localhost:8200/classifiers/reload
```

---

## 12. TypeScript client (packages/ml-client/src/classifier-client.ts)

```typescript
import { MLServiceClient } from "./index"
import type { ClassifyIntentRequest, ClassifyIntentResponse } from "./types"

export interface FormationResult { formation: string; confidence: number; model: string }
export interface YieldResult { yield_class: string; confidence: number; model: string }
export interface DuplicateResult {
  is_likely_duplicate: boolean
  candidates: Array<{ member_id: string; full_name: string; similarity_score: number; match_reason: string }>
}
export interface AnomalyResult {
  agent_id: string
  anomaly_score: number
  is_anomalous: boolean
  explanation: string
}

export class ClassifierClient extends MLServiceClient {
  async classifyIntent(req: ClassifyIntentRequest): Promise<ClassifyIntentResponse> {
    return this.post("/classifiers/intent", req)
  }

  async classifyFormation(args: { description: string }): Promise<FormationResult> {
    return this.post("/classifiers/formation", args)
  }

  async predictYield(args: { formation: string; depth_m: number; gps_lat?: number; gps_lng?: number }): Promise<YieldResult> {
    return this.post("/classifiers/yield", args)
  }

  async checkDuplicate(args: {
    first_name: string
    last_name: string
    phone?: string
    dob?: string
    existing_members?: unknown[]
  }): Promise<DuplicateResult> {
    return this.post("/classifiers/duplicate", args)
  }

  async detectAnomaly(args: { agent_id: string; action_sequence: string[] }): Promise<AnomalyResult> {
    return this.post("/classifiers/anomaly", args)
  }
}
```

---

## 13. keprix tool implementations

Replace stubs from 229:

```typescript
{
  name: "classify_intent",
  handler: async (args) => classifierClient.classifyIntent(args),
},
{
  name: "classify_formation",
  handler: async (args: { description: string }) => classifierClient.classifyFormation(args),
},
{
  name: "predict_yield",
  handler: async (args) => classifierClient.predictYield(args),
},
{
  name: "check_duplicate_member",
  handler: async (args) => {
    // Fetch existing members from ABBIS database before calling
    const existing = await fetchExistingMembers()  // implement in keprix ABBIS agent
    return classifierClient.checkDuplicate({ ...args, existing_members: existing })
  },
},
{
  name: "detect_agent_anomaly",
  handler: async (args) => classifierClient.detectAnomaly(args),
},
```

---

## 14. Integration with keprix mutation engine (Prompt 28)

Before the mutation engine executes any write action, call the anomaly detector if the action involves financial data, member record updates, or election state:

```typescript
// In keprix mutation engine, before executing a mutation:
if (SENSITIVE_MUTATION_TYPES.includes(mutation.type)) {
  const anomaly = await callTool("detect_agent_anomaly", {
    agent_id: mutation.agent_id,
    action_sequence: mutation.action_history,
  })
  if (anomaly.is_anomalous) {
    mutation.status = "flagged"
    mutation.flag_reason = anomaly.explanation
    await notifyAdmin(mutation)
    return  // do not execute; await admin review
  }
}
```

This is the only place in the keprix codebase that calls `detect_agent_anomaly` autonomously. All other tool calls are agent-driven.

---

## 15. Acceptance criteria

1. `POST /classifiers/intent` with text `"how much to drill a borehole in Accra"` returns `{ "intent": "quote_request", ... }`
2. `POST /classifiers/formation` with `"red laterite then decomposed granite to 8m"` returns `{ "formation": "laterite", ... }` or `"saprolite"` (either is acceptable from rules; document which is returned)
3. `POST /classifiers/yield` with `{ "formation": "alluvium", "depth_m": 30 }` returns `{ "yield_class": "community", ... }`
4. `POST /classifiers/duplicate` with a name matching an existing member at 90%+ returns `{ "is_likely_duplicate": true, ... }`
5. `POST /classifiers/anomaly` with a never-seen action sequence returns `{ "is_anomalous": true, "anomaly_score": 1.0 }`
6. Every inference call creates a record in `ml_training_log`
7. `PATCH /classifiers/training-log/{id}/label` updates the label field
8. `GET /classifiers/training-log/intent/unlabeled` returns unlabeled intent records
9. `POST /classifiers/reload` after placing a new `intent_v1.joblib` causes the next prediction to use the new model
10. All five keprix tools (`classify_intent`, `classify_formation`, `predict_yield`, `check_duplicate_member`, `detect_agent_anomaly`) return structured responses, not 500 errors, when called before any ML model is trained
11. Mutation engine anomaly gate: a flagged mutation must NOT execute; admin notification must be sent

---

## 16. Data targets before ML upgrade

| Classifier | Target labeled records | Expected timeframe |
|---|---|---|
| Intent | 50 per class (350 total) | 2-3 months of active WhatsApp use |
| Formation | 30 per class (240 total) | 4-6 months of drilling log submissions |
| Yield predictor | 200 completed logs | 6-12 months of log data |
| Duplicate detector | ML upgrade when member count reaches 500 | Membership growth dependent |
| Anomaly detector | 1000 logged action sequences | 2-3 months of agent activity |
