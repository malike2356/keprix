"""LLM inference for deep research via the workspace provider stack."""

from __future__ import annotations

from keprix.api.chat_inference import complete_chat_completion
from keprix.research.errors import ResearchConfigError, ResearchPipelineError


async def complete_research_prompt(
    prompt: str,
    *,
    model: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> str:
    try:
        result = await complete_chat_completion(
            user_text=prompt,
            model_id=model,
            user_id=user_id,
            session_id=session_id,
            channel="research",
            include_codebase_context=False,
        )
    except RuntimeError as exc:
        raise ResearchConfigError(str(exc)) from exc

    text = result.text.strip()
    if not text:
        raise ResearchPipelineError("LLM returned an empty research response.")
    return text
