"""Follow-up prompt generation in the user's language."""

from __future__ import annotations

from keprix.backend.intent.registry import get_intent_registry
from keprix.backend.intent.schemas import IntentExtractionResult


def entity_display_name(field_name: str) -> str:
    return field_name.replace("_", " ")


class FollowUpGenerator:
    async def generate(
        self,
        result: IntentExtractionResult,
        user_language: str,
        workspace_id: str,
    ) -> IntentExtractionResult:
        if not result.missing_required:
            result.follow_up_prompt = None
            return result

        schema = get_intent_registry().get_schema(result.intent, result.domain)
        if not schema or not schema.follow_up_template:
            result.follow_up_prompt = None
            return result

        field_names = ", ".join(entity_display_name(name) for name in result.missing_required)
        english_prompt = schema.follow_up_template.replace("{missing_fields}", field_names)

        if user_language.split("-")[0].lower() == "en":
            result.follow_up_prompt = english_prompt
            return result

        from keprix.backend.localization.translation import translate_text

        translation = await translate_text(
            workspace_id=workspace_id,
            text=english_prompt,
            source_language="en",
            target_language=user_language,
        )
        result.follow_up_prompt = translation.translated_text
        return result


_follow_up_generator: FollowUpGenerator | None = None


def get_follow_up_generator() -> FollowUpGenerator:
    global _follow_up_generator
    if _follow_up_generator is None:
        _follow_up_generator = FollowUpGenerator()
    return _follow_up_generator
