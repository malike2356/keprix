"""Register Clinicom tools on the pack registry."""

from __future__ import annotations

from tools.handlers import (
    clinicom_cultural_adapt_handler,
    clinicom_confidence_explain_handler,
    clinicom_product_help_handler,
    clinicom_simplify_handler,
    clinicom_speak_handler,
    clinicom_safety_triage_assist_handler,
    clinicom_session_digest_handler,
    clinicom_specialty_simplify_handler,
    clinicom_teachback_score_handler,
    clinicom_transcribe_handler,
    clinicom_translate_handler,
)
from tools.registry import registry

registry.register("clinicom_transcribe", clinicom_transcribe_handler)
registry.register("clinicom_translate", clinicom_translate_handler)
registry.register("clinicom_simplify", clinicom_simplify_handler)
registry.register("clinicom_speak", clinicom_speak_handler)
registry.register("clinicom_cultural_adapt", clinicom_cultural_adapt_handler)
registry.register("clinicom_teachback_score", clinicom_teachback_score_handler)
registry.register("clinicom_safety_triage_assist", clinicom_safety_triage_assist_handler)
registry.register("clinicom_session_digest", clinicom_session_digest_handler)
registry.register("clinicom_specialty_simplify", clinicom_specialty_simplify_handler)
registry.register("clinicom_confidence_explain", clinicom_confidence_explain_handler)
registry.register("clinicom_product_help", clinicom_product_help_handler)
