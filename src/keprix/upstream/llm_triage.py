"""Optional LLM-assisted triage notes for upstream features."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from keprix.upstream.hermes_monitor import UpstreamFeature


def maybe_llm_triage(feature: UpstreamFeature) -> str:
    """Append an LLM draft when KEPRIX_UPSTREAM_LLM_TRIAGE is truthy.

    Disabled by default. Failures never block the monitor; returns empty string.
    """
    flag = (os.environ.get("KEPRIX_UPSTREAM_LLM_TRIAGE") or "").strip().lower()
    if flag not in {"1", "true", "yes", "on"}:
        return ""
    try:
        # Prefer a tiny local draft helper if the agent package exposes one.
        try:
            from keprix.agent.auxiliary_client import run_auxiliary_text  # type: ignore
        except Exception:
            run_auxiliary_text = None

        prompt = (
            "Summarize in 2 sentences whether Keprix should adopt this Hermes feature, "
            "what to harden, and where it likely belongs in a Python agent OS.\n\n"
            f"Name: {feature.name}\n"
            f"Category: {feature.category.value}\n"
            f"Description: {feature.description}\n"
            f"Suggested: {feature.suggested_status.value if feature.suggested_status else 'unevaluated'}\n"
        )
        if callable(run_auxiliary_text):
            result = run_auxiliary_text(prompt)
            if isinstance(result, str) and result.strip():
                return result.strip()[:800]
        # Fallback deterministic assist so enabling the flag still adds value offline.
        return (
            f"Review `{feature.category.value}` change `{feature.name[:80]}` for Keprix fit; "
            "prefer rebuild over merge, and harden tools/network/memory before default enable."
        )
    except Exception:
        logger.debug("optional LLM triage skipped", exc_info=True)
        return ""
