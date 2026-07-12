"""Onboarding Path Builder entrypoint."""
from __future__ import annotations
from typing import Any
from keprix.agent_os.workflows.onboarding_path import generate_onboarding_path

def run(input_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    form = (context or {}).get("form") or {}
    product = str(form.get("product") or input_text or "").strip()
    audience = str(form.get("audience") or "new users")
    return generate_onboarding_path(product=product, audience=audience)
