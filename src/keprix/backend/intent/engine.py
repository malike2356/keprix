"""Main structured intent extraction logic."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from keprix.backend.intent.follow_up import get_follow_up_generator
from keprix.backend.intent.registry import get_intent_registry
from keprix.backend.intent.schemas import EXTRACTION_JSON_SCHEMA, IntentExtractionResult, IntentSchema
from keprix.backend.intent.validator import get_intent_validator

logger = logging.getLogger(__name__)

_GREETING_TERMS = (
    "mema wo akye",
    "good morning",
    "good afternoon",
    "hello",
    "hi there",
    "hi",
)
_CANCEL_TERMS = {"daabi", "no", "stop", "cancel", "nope"}
_CONFIRM_TERMS = {"aane", "yoo", "yes", "correct", "that is correct"}
_NOISE_RE = re.compile(r"^[a-z]{6,}$")
_LOCATION_RE = re.compile(
    r"\b(?:near|around|in|at)\s+([A-Za-z][A-Za-z\s\-]{1,40})",
    re.I,
)


class IntentExtractionEngine:
    async def extract(
        self,
        translated_text: str,
        original_text: str,
        source_language: str,
        workspace_id: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> IntentExtractionResult:
        registry = get_intent_registry()
        schemas = registry.get_schemas_for_workspace(workspace_id)
        heuristic = self._heuristic_extract(
            translated_text=translated_text,
            original_text=original_text,
            schemas=schemas,
        )
        if heuristic is not None:
            raw_result = heuristic
        else:
            raw_result = await self._llm_extract(
                translated_text=translated_text,
                original_text=original_text,
                source_language=source_language,
                workspace_id=workspace_id,
                schemas=schemas,
                conversation_history=conversation_history,
            )

        result = self._parse_raw_result(raw_result, schemas, source_language)
        result = await get_intent_validator().validate_and_fill(
            result,
            schemas,
            translated_text,
            original_text,
        )
        result = await get_follow_up_generator().generate(result, source_language, workspace_id)
        return result

    def build_user_message(
        self,
        translated: str,
        original: str,
        lang: str,
        history: list[dict[str, Any]] | None,
    ) -> str:
        history_str = ""
        if history:
            last_turns = history[-3:]
            history_str = "\n\nRecent conversation:\n" + "\n".join(
                f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in last_turns
            )
        return (
            f"Original language: {lang}\n"
            f"Original message: {original}\n"
            f"Translated message (English): {translated}{history_str}\n\n"
            "Extract the intent and entities."
        )

    def build_schema_prompt(self, schemas: list[IntentSchema]) -> str:
        lines: list[str] = []
        for schema in schemas:
            entity_list = ", ".join(
                f"{entity.name} ({'required' if entity.required else 'optional'}, {entity.type})"
                + (f" [{'/'.join(entity.enum_values)}]" if entity.enum_values else "")
                for entity in schema.entities
            )
            lines.append(f"- {schema.name} [{schema.domain}]: {schema.description}")
            if entity_list:
                lines.append(f"  Entities: {entity_list}")
            if schema.examples:
                lines.append(f"  Examples: {'; '.join(schema.examples[:2])}")
        return "\n".join(lines)

    def _system_prompt(self, schema_descriptions: str, source_language: str) -> str:
        return (
            "You are an intent classifier for a multilingual AI assistant.\n\n"
            f"The user's message has been translated from {source_language} to English.\n"
            "You must extract the user's intent and any entities from the translated message.\n\n"
            f"Available intents:\n{schema_descriptions}\n\n"
            "Rules:\n"
            "- Choose the single best matching intent.\n"
            "- Extract all entities you can find in the message.\n"
            "- If an entity is not present, set its value to null.\n"
            "- Set confidence to a number from 0.0 to 1.0 based on how certain you are.\n"
            "- If no intent matches well, use 'fallback' with confidence below 0.5.\n"
            "- For location entities, preserve the exact place name from the translated text.\n"
            "- Respond only with the JSON object. No prose.\n"
        )

    def _heuristic_extract(
        self,
        *,
        translated_text: str,
        original_text: str,
        schemas: list[IntentSchema],
    ) -> dict[str, Any] | None:
        translated = translated_text.strip()
        original = original_text.strip()
        translated_lower = translated.lower()
        original_lower = original.lower()

        if not translated and not original:
            return {
                "intent": "fallback",
                "domain": "generic",
                "confidence": 0.1,
                "entities": {},
                "extraction_notes": "Empty input",
            }

        if any(term in original_lower or term in translated_lower for term in _GREETING_TERMS):
            return {
                "intent": "greeting",
                "domain": "generic",
                "confidence": 0.9,
                "entities": {},
                "extraction_notes": None,
            }

        if original_lower in _CANCEL_TERMS or translated_lower in _CANCEL_TERMS:
            return {
                "intent": "cancel",
                "domain": "generic",
                "confidence": 0.88,
                "entities": {},
                "extraction_notes": None,
            }

        if original_lower in _CONFIRM_TERMS or translated_lower in _CONFIRM_TERMS:
            return {
                "intent": "confirm",
                "domain": "generic",
                "confidence": 0.86,
                "entities": {},
                "extraction_notes": None,
            }

        if self._looks_like_noise(translated_lower):
            return {
                "intent": "fallback",
                "domain": "generic",
                "confidence": 0.2,
                "entities": {"raw_query": translated_text},
                "extraction_notes": "Unrecognised input",
            }

        matched = self._match_keyword_triggers(translated, translated_lower, schemas)
        if matched is not None:
            return matched

        return None

    def _match_keyword_triggers(
        self,
        translated: str,
        translated_lower: str,
        schemas: list[IntentSchema],
    ) -> dict[str, Any] | None:
        for schema in schemas:
            triggers = schema.keyword_triggers or {}
            required_all = [str(item).lower() for item in triggers.get("all") or []]
            required_any = [str(item).lower() for item in triggers.get("any") or []]
            if not required_all and not required_any:
                continue
            if required_all and not all(term in translated_lower for term in required_all):
                continue
            if required_any and not any(term in translated_lower for term in required_any):
                continue
            if not self._schema_available(schema.name, schemas):
                continue
            entities = {entity.name: None for entity in schema.entities}
            entities.update(self._apply_heuristic_extractors(schema, translated))
            return {
                "intent": schema.name,
                "domain": schema.domain,
                "confidence": 0.88,
                "entities": entities,
                "extraction_notes": None,
            }
        return None

    def _apply_heuristic_extractors(
        self,
        schema: IntentSchema,
        translated: str,
    ) -> dict[str, Any]:
        extractors = schema.heuristic_extractors or {}
        values: dict[str, Any] = {}
        for entity_name, extractor_id in extractors.items():
            if extractor_id == "location_near":
                values[entity_name] = self._extract_location(translated)
            elif extractor_id == "depth_metres":
                values[entity_name] = self._extract_depth_metres(translated)
        return values

    async def _llm_extract(
        self,
        *,
        translated_text: str,
        original_text: str,
        source_language: str,
        workspace_id: str,
        schemas: list[IntentSchema],
        conversation_history: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        if os.environ.get("KEPRIX_INTENT_HEURISTIC_ONLY", "").lower() in {"1", "true", "yes"}:
            return {
                "intent": "fallback",
                "domain": "generic",
                "confidence": 0.35,
                "entities": {"raw_query": translated_text},
                "extraction_notes": "Heuristic-only mode",
            }

        schema_descriptions = self.build_schema_prompt(schemas)
        system_prompt = self._system_prompt(schema_descriptions, source_language)
        user_message = self.build_user_message(
            translated_text,
            original_text,
            source_language,
            conversation_history,
        )

        try:
            from agent.plugin_llm import PluginLlm, PluginLlmTextInput

            llm = PluginLlm(plugin_id="keprix-intent")
            completion = await llm.acomplete_structured(
                instructions=system_prompt,
                input=[PluginLlmTextInput(text=user_message)],
                json_schema=EXTRACTION_JSON_SCHEMA,
                purpose="intent_extraction",
            )
            if completion.parsed:
                return completion.parsed
            if completion.text:
                import json

                return json.loads(completion.text)
        except Exception as exc:
            logger.debug("Intent LLM extraction failed, using fallback: %s", exc)

        return {
            "intent": "fallback",
            "domain": "generic",
            "confidence": 0.35,
            "entities": {"raw_query": translated_text},
            "extraction_notes": "LLM extraction unavailable",
        }

    def _parse_raw_result(
        self,
        raw: dict[str, Any],
        schemas: list[IntentSchema],
        source_language: str,
    ) -> IntentExtractionResult:
        intent_name = str(raw.get("intent") or "fallback")
        domain = str(raw.get("domain") or "generic")
        schema = get_intent_registry().find_schema(intent_name, schemas)
        if schema:
            domain = schema.domain
        confidence = float(raw.get("confidence", 0.5))
        entities = dict(raw.get("entities") or {})
        return IntentExtractionResult(
            intent=intent_name,
            confidence=max(0.0, min(1.0, confidence)),
            original_language=source_language,
            domain=domain,
            entities=entities,
            extraction_notes=raw.get("extraction_notes"),
        )

    def _schema_available(self, name: str, schemas: list[IntentSchema]) -> bool:
        return any(row.name == name for row in schemas)

    def _looks_like_noise(self, text: str) -> bool:
        compact = re.sub(r"[^a-z]", "", text.lower())
        if len(compact) < 8:
            return False
        if " " in text:
            return False
        vowels = sum(1 for ch in compact if ch in "aeiou")
        return vowels <= 2 or _NOISE_RE.match(compact) is not None

    def _extract_location(self, translated: str) -> str | None:
        match = _LOCATION_RE.search(translated)
        if match:
            return f"near {match.group(1).strip()}"
        return None

    def _extract_depth_metres(self, translated: str) -> float | None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:m\b|metres?|meters?)", translated, re.I)
        if match:
            return float(match.group(1))
        return None


_engine: IntentExtractionEngine | None = None


def get_intent_engine() -> IntentExtractionEngine:
    global _engine
    if _engine is None:
        _engine = IntentExtractionEngine()
    return _engine
