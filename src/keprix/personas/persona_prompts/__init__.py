"""Registry of engineered persona prompts."""

from __future__ import annotations

from keprix.personas.persona_prompts.beacon import BEACON_PROMPT
from keprix.personas.persona_prompts.codex import CODEX_PROMPT
from keprix.personas.persona_prompts.compass import COMPASS_PROMPT
from keprix.personas.persona_prompts.echo import ECHO_PROMPT
from keprix.personas.persona_prompts.ember import EMBER_PROMPT
from keprix.personas.persona_prompts.forge import FORGE_PROMPT
from keprix.personas.persona_prompts.nexus import NEXUS_PROMPT
from keprix.personas.persona_prompts.prism import PRISM_PROMPT
from keprix.personas.persona_prompts.sage import SAGE_PROMPT
from keprix.personas.persona_prompts.warden import WARDEN_PROMPT

ENGINEERED_PERSONA_PROMPTS: dict[str, str] = {
    "NEXUS": NEXUS_PROMPT,
    "FORGE": FORGE_PROMPT,
    "WARDEN": WARDEN_PROMPT,
    "SAGE": SAGE_PROMPT,
    "BEACON": BEACON_PROMPT,
    "PRISM": PRISM_PROMPT,
    "COMPASS": COMPASS_PROMPT,
    "EMBER": EMBER_PROMPT,
    "CODEX": CODEX_PROMPT,
    "ECHO": ECHO_PROMPT,
}


def get_engineered_prompt(persona_name: str) -> str | None:
    """Return the engineered prompt for a persona, or None if not defined."""
    return ENGINEERED_PERSONA_PROMPTS.get(persona_name.upper())
