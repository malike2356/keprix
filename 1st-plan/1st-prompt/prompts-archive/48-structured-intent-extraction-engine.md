# keprix - Prompt 48: Structured Intent Extraction Engine

## Context

Read `35-localization-language-voice.md` and `93-african-language-provider-adapters.md` first.

Prompt 27's runtime flow includes step 6: "Extract intent and entities from the translated text and the original text." This prompt implements that step as a first-class module with a typed output schema, a domain-pack registration API, LLM-backed extraction with JSON mode, entity validation, missing-field detection, and follow-up prompt generation in the user's language.

This module sits between the translation layer and the business logic (tools, playbooks). It is the most architecturally important addition in the localization stack because it breaks the chain of ambiguity: after this module runs, downstream code operates on a typed, validated object - not a translated string whose accuracy cannot be guaranteed.

Without structured intent extraction, a translation error propagates into tool calls and playbook steps. With it, translation errors affect the text representation of an entity value (e.g., a location name is slightly wrong) but they cannot cause the wrong tool to be called or the wrong playbook branch to execute.

---

## Design Principles

**Language-agnostic business logic.** A borehole quote request arrives as `{intent: "request_drilling_quote", entities: {...}}` regardless of whether the user spoke in Twi, typed in Dagbani, or wrote in English. The playbook code never sees the language.

**Domain-configurable.** keprix ships generic intents. Domain packs (Prompt 30) register their own intent schemas. The extraction engine uses whatever schemas are loaded for the current workspace.

**Dual-text extraction.** The engine receives both the translated text (English) and the original text (local language). It uses the translated text as the primary input but references the original when entities extracted from the translation look suspicious (e.g., a place name mangled in translation might be preserved correctly in the original).

**Confidence and follow-up.** Every extraction result includes a confidence score and, when required entities are missing, a follow-up prompt rendered in the user's language ready to send back.

---

## File Structure

```
keprix/backend/intent/
    __init__.py
    engine.py           - main extraction logic
    registry.py         - intent schema registration and lookup
    schemas.py          - typed models for intent results and schemas
    validator.py        - entity validation and missing-field detection
    follow_up.py        - follow-up prompt generation in user's language
    generic_intents.py  - built-in generic intent schemas
    routes.py           - API endpoints

keprix/tests/intent/
    test_engine.py
    test_registry.py
    test_validator.py
    test_follow_up.py
    fixtures/           - sample intent extraction inputs and expected outputs
```

---

## Intent Schema Model

Domain packs and built-in definitions use this schema:

```python
# keprix/backend/intent/schemas.py

from pydantic import BaseModel
from typing import Any

class EntitySchema(BaseModel):
    name: str
    type: str
    # 'string', 'number', 'boolean', 'location', 'date', 'currency', 'enum', 'list'
    required: bool = False
    enum_values: list[str] | None = None
    # only if type == 'enum'
    description: str = ""
    # included in the LLM extraction prompt to clarify what this entity is
    example_values: list[str] | None = None
    # shown to LLM as examples

class IntentSchema(BaseModel):
    name: str
    # snake_case identifier, e.g. 'request_drilling_quote'
    description: str
    # one or two sentences for the LLM prompt
    domain: str
    # 'generic', 'borehole_drilling', 'compass_compliance', etc.
    entities: list[EntitySchema]
    follow_up_template: str
    # English template for follow-up questions when required entities are missing.
    # Use {missing_fields} placeholder. Gets translated to user's language.
    examples: list[str] | None = None
    # example user utterances that should match this intent; helps the LLM

class IntentExtractionResult(BaseModel):
    intent: str
    # matched intent name, e.g. 'request_drilling_quote'
    confidence: float
    # 0.0 - 1.0; how confident the LLM is in this intent
    original_language: str
    # BCP 47 code of the user's input language
    domain: str
    entities: dict[str, Any]
    # extracted entity values; key = entity name, value = extracted value or None
    missing_required: list[str]
    # entity names that are required but not present in the input
    follow_up_prompt: str | None
    # ready-to-send follow-up question in user's language; None if all required fields present
    extraction_notes: str | None
    # LLM's own notes on ambiguity or edge cases (for human review)
```

---

## Generic Built-In Intents

```python
# keprix/backend/intent/generic_intents.py

GENERIC_INTENTS = [
    IntentSchema(
        name="ask_question",
        description="The user is asking for information or an explanation.",
        domain="generic",
        entities=[
            EntitySchema(name="topic", type="string", required=False,
                         description="The subject the user is asking about"),
        ],
        follow_up_template="Could you tell me more about what you need to know regarding {missing_fields}?",
        examples=["What is the water table depth here?", "How much does this cost?"],
    ),
    IntentSchema(
        name="make_request",
        description="The user wants something done: a quote, a visit, a report, a calculation.",
        domain="generic",
        entities=[
            EntitySchema(name="request_type", type="string", required=True,
                         description="What the user wants done"),
            EntitySchema(name="target", type="string", required=False,
                         description="What the request is for"),
        ],
        follow_up_template="What would you like me to do with {missing_fields}?",
    ),
    IntentSchema(
        name="provide_information",
        description="The user is supplying information requested in a previous turn.",
        domain="generic",
        entities=[
            EntitySchema(name="information_type", type="string", required=False),
            EntitySchema(name="value", type="string", required=True),
        ],
        follow_up_template="",
    ),
    IntentSchema(
        name="confirm",
        description="The user is confirming, agreeing, or saying yes.",
        domain="generic",
        entities=[],
        follow_up_template="",
        examples=["Yes", "That is correct", "Aane", "Yoo"],
    ),
    IntentSchema(
        name="cancel",
        description="The user is cancelling, stopping, or saying no.",
        domain="generic",
        entities=[],
        follow_up_template="",
        examples=["No", "Stop", "Cancel", "Daabi"],
    ),
    IntentSchema(
        name="request_help",
        description="The user needs help or does not understand.",
        domain="generic",
        entities=[],
        follow_up_template="",
    ),
    IntentSchema(
        name="greeting",
        description="The user is greeting or starting a conversation.",
        domain="generic",
        entities=[],
        follow_up_template="",
    ),
    IntentSchema(
        name="fallback",
        description="The input did not match any specific intent with sufficient confidence.",
        domain="generic",
        entities=[
            EntitySchema(name="raw_query", type="string", required=False),
        ],
        follow_up_template="I was not sure what you needed. Could you tell me more about {missing_fields}?",
    ),
]
```

---

## Intent Registry

```python
# keprix/backend/intent/registry.py

class IntentRegistry:
    """
    Holds all registered intent schemas for this keprix instance.
    Domain packs register their schemas at load time via Prompt 07's skill loader.
    """

    def __init__(self):
        self._schemas: dict[str, list[IntentSchema]] = {}
        # keyed by domain name

        # Register generic intents on init
        for schema in GENERIC_INTENTS:
            self.register(schema)

    def register(self, schema: IntentSchema) -> None:
        domain = schema.domain
        if domain not in self._schemas:
            self._schemas[domain] = []
        existing = next((s for s in self._schemas[domain] if s.name == schema.name), None)
        if existing:
            self._schemas[domain].remove(existing)
        self._schemas[domain].append(schema)

    def get_schemas_for_workspace(self, workspace_id: str) -> list[IntentSchema]:
        """
        Returns all schemas available for this workspace.
        Includes generic intents + any domain pack intents loaded for this workspace.
        """
        loaded_domains = skill_loader.get_loaded_domains(workspace_id)
        schemas = list(self._schemas.get("generic", []))
        for domain in loaded_domains:
            schemas.extend(self._schemas.get(domain, []))
        return schemas

    def get_schema(self, name: str, domain: str = "generic") -> IntentSchema | None:
        return next((s for s in self._schemas.get(domain, []) if s.name == name), None)

    def list_domains(self) -> list[str]:
        return list(self._schemas.keys())

# Global singleton
intent_registry = IntentRegistry()
```

Domain packs register their intents during pack load (Prompt 07):

```python
# In the borehole-africa domain pack's __init__.py:
from keprix.backend.intent.registry import intent_registry

intent_registry.register(IntentSchema(
    name="request_drilling_quote",
    domain="borehole_drilling",
    description="The user wants a price estimate or quote for drilling a new borehole.",
    entities=[
        EntitySchema(name="location_description", type="string", required=True,
                     description="Village, district, region, or GPS location",
                     example_values=["near Tamale", "Ashanti Region", "Kumasi Metropolitan"]),
        EntitySchema(name="depth_target_metres", type="number", required=False,
                     description="Expected or required depth of the borehole in metres"),
        EntitySchema(name="community_size_households", type="number", required=False,
                     description="Number of households the borehole will serve"),
        EntitySchema(name="casing_type", type="enum", required=False,
                     enum_values=["PVC", "steel", "unknown"],
                     description="Type of casing material"),
        EntitySchema(name="pump_required", type="boolean", required=False),
        EntitySchema(name="budget_range", type="string", required=False),
        EntitySchema(name="urgency", type="enum", required=False,
                     enum_values=["urgent", "normal", "planning_only"]),
    ],
    follow_up_template="To give you a quote, I need: {missing_fields}. Please provide these.",
    examples=[
        "Me pe borehole quote for my village near Kumasi",
        "How much will it cost to drill in Tamale?",
        "I need a price for a borehole in Volta Region",
    ],
))
```

---

## Extraction Engine

```python
# keprix/backend/intent/engine.py

class IntentExtractionEngine:

    async def extract(
        self,
        translated_text: str,
        original_text: str,
        source_language: str,
        workspace_id: str,
        conversation_history: list[dict] | None = None,
    ) -> IntentExtractionResult:
        """
        Main extraction entry point.
        Returns a typed, validated IntentExtractionResult.
        """
        schemas = intent_registry.get_schemas_for_workspace(workspace_id)
        schema_descriptions = self._build_schema_prompt(schemas)

        # Build LLM prompt for intent extraction
        system_prompt = self._system_prompt(schema_descriptions, source_language)
        user_message = self._user_message(translated_text, original_text, source_language,
                                           conversation_history)

        # Call LLM in JSON mode
        raw_result = await llm_router.complete_json(
            system=system_prompt,
            user=user_message,
            response_schema=EXTRACTION_JSON_SCHEMA,
            workspace_id=workspace_id,
            model_preference="fast_and_capable",
            # intent extraction runs on every message; keep it fast
        )

        result = self._parse_raw_result(raw_result, schemas, source_language)
        result = await validator.validate_and_fill(result, schemas, translated_text, original_text)
        result = await follow_up_generator.generate(result, source_language, workspace_id)

        return result

    def _system_prompt(self, schema_descriptions: str, source_language: str) -> str:
        return f"""You are an intent classifier for a multilingual AI assistant.

The user's message has been translated from {source_language} to English.
You must extract the user's intent and any entities from the translated message.

Available intents:
{schema_descriptions}

Rules:
- Choose the single best matching intent.
- Extract all entities you can find in the message.
- If an entity is not present, set its value to null.
- Set confidence to a number from 0.0 to 1.0 based on how certain you are of the intent match.
- If the message could match multiple intents, choose the one with the highest confidence and note ambiguity in extraction_notes.
- If no intent matches well, use 'fallback' with confidence below 0.5.
- For location entities, preserve the exact place name from the translated text; do not normalise or infer.
- For number entities, extract the numeric value without units; store units separately if present.
- Respond only with the JSON object. No prose.
"""

    def _user_message(self, translated: str, original: str, lang: str,
                      history: list[dict] | None) -> str:
        history_str = ""
        if history:
            last_turns = history[-3:]  # last 3 turns for context
            history_str = "\n\nRecent conversation:\n" + "\n".join(
                f"{t['role']}: {t['content']}" for t in last_turns
            )
        return f"""Original language: {lang}
Original message: {original}
Translated message (English): {translated}{history_str}

Extract the intent and entities."""

    def _build_schema_prompt(self, schemas: list[IntentSchema]) -> str:
        lines = []
        for s in schemas:
            entity_list = ", ".join(
                f"{e.name} ({'required' if e.required else 'optional'}, {e.type})"
                + (f" [{'/'.join(e.enum_values)}]" if e.enum_values else "")
                for e in s.entities
            )
            lines.append(f"- {s.name}: {s.description}")
            if entity_list:
                lines.append(f"  Entities: {entity_list}")
            if s.examples:
                lines.append(f"  Examples: {'; '.join(s.examples[:2])}")
        return "\n".join(lines)
```

### JSON Schema for LLM Response

```python
EXTRACTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "entities": {"type": "object"},
        "extraction_notes": {"type": ["string", "null"]},
    },
    "required": ["intent", "confidence", "entities"],
}
```

---

## Validator

```python
# keprix/backend/intent/validator.py

class IntentEntityValidator:

    async def validate_and_fill(
        self,
        result: IntentExtractionResult,
        schemas: list[IntentSchema],
        translated_text: str,
        original_text: str,
    ) -> IntentExtractionResult:
        """
        Post-processes the LLM output:
        - Validates entity types against the schema.
        - Identifies required fields that are missing.
        - Attempts a second-pass extraction from original_text for entities
          that came back null but might be in the original.
        """
        schema = next((s for s in schemas if s.name == result.intent), None)
        if not schema:
            result.intent = "fallback"
            result.confidence = 0.3
            return result

        # Validate enum values
        for entity_schema in schema.entities:
            value = result.entities.get(entity_schema.name)
            if value and entity_schema.type == "enum":
                if entity_schema.enum_values and value not in entity_schema.enum_values:
                    result.entities[entity_schema.name] = None
                    # invalid enum: treat as missing

        # Identify missing required fields
        result.missing_required = [
            e.name for e in schema.entities
            if e.required and (
                result.entities.get(e.name) is None
                or result.entities.get(e.name) == ""
            )
        ]

        return result
```

---

## Follow-Up Prompt Generator

```python
# keprix/backend/intent/follow_up.py

class FollowUpGenerator:

    async def generate(
        self,
        result: IntentExtractionResult,
        user_language: str,
        workspace_id: str,
    ) -> IntentExtractionResult:
        """
        If required entities are missing, generates a follow-up question in the user's language.
        """
        if not result.missing_required:
            result.follow_up_prompt = None
            return result

        schema = intent_registry.get_schema(result.intent, result.domain)
        if not schema or not schema.follow_up_template:
            result.follow_up_prompt = None
            return result

        # Format the template with human-readable field names
        field_names = ", ".join(
            entity_display_name(f) for f in result.missing_required
        )
        english_prompt = schema.follow_up_template.replace("{missing_fields}", field_names)

        # Translate to user's language if not English
        if not user_language.startswith("en"):
            translation = await localization_module.translate(
                text=english_prompt,
                source_language="en",
                target_language=user_language,
                workspace_id=workspace_id,
            )
            result.follow_up_prompt = translation.translated_text
        else:
            result.follow_up_prompt = english_prompt

        return result
```

---

## Integration With Runtime Flow

The intent extraction engine is called from `keprix/backend/gateway/language_middleware.py` (Prompt 27). After translation completes (step 5 of the runtime flow), insert:

```python
# In language_middleware.py, after translation:
if localization_config.intent_extraction_enabled:
    intent_result = await intent_engine.extract(
        translated_text=translation_result.translated_text,
        original_text=message.original_text,
        source_language=message.detected_language,
        workspace_id=message.workspace_id,
        conversation_history=message.context.history,
    )
    message.context.intent = intent_result

    # If a follow-up is needed and confidence is high enough,
    # return the follow-up immediately without running tools
    if intent_result.follow_up_prompt and intent_result.confidence > 0.6:
        return LocalizationResponse(
            text=intent_result.follow_up_prompt,
            intent=intent_result,
            requires_follow_up=True,
        )
```

The agent and playbooks access the intent via `message.context.intent`. A playbook step can check:

```python
if context.intent.intent == "request_drilling_quote":
    location = context.intent.entities.get("location_description")
    depth = context.intent.entities.get("depth_target_metres")
    # ... proceed with quote logic
```

---

## API Endpoints

```
POST /api/intent/extract
     Requires workspace auth.
     Body: {
       translated_text: string,
       original_text: string,
       source_language: string,
       conversation_history?: array
     }
     Returns: IntentExtractionResult

GET  /api/intent/schemas
     Returns: all registered intent schemas for this workspace (names, descriptions, entities)

GET  /api/intent/schemas/{domain}
     Returns: intent schemas for a specific domain

POST /api/intent/register
     Admin only. Registers a new intent schema at runtime (for testing; production registration via domain packs).
     Body: IntentSchema
```

---

## Acceptance Criteria

- `extract("I want a borehole quote near Tamale", ..., workspace with borehole pack)` returns `intent = "request_drilling_quote"`, `entities.location_description = "near Tamale"`, `missing_required` contains `depth_target_metres` (required but not stated).
- `extract("Mema wo akye", ..., any workspace)` returns `intent = "greeting"`, `confidence >= 0.8`.
- `extract("Daabi", ..., any workspace)` returns `intent = "cancel"`.
- `extract("gjhsadfkjhsad random noise", ...)` returns `intent = "fallback"`, `confidence < 0.5`.
- When `missing_required` is non-empty, `follow_up_prompt` is set in the user's language.
- When all required entities are present, `follow_up_prompt` is `None`.
- An intent registered by a domain pack is returned in `GET /api/intent/schemas/{domain}`.
- A domain pack unregistered from the workspace does not appear in extraction schemas.
- Entity type validation: if `casing_type` receives `"concrete"` (not in enum), it is set to `None` and the field appears in `missing_required`.
- Conversation history from the last 3 turns is included in the extraction context.
- `extract` call completes in under 2 seconds for a standard 4k context model.
