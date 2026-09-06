"""Vision-backed floor-plan extraction; output remains a user-confirmed proposal."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix.property_calculators.floor_plan_compliance import (
    floor_plan_vision_prompt,
    parse_floor_plan_vision_proposal,
)


def analyze_image(image_path: str, *, mode: str = "boq", model: str | None = None) -> dict[str, Any]:
    path = Path(image_path).expanduser()
    if not path.is_file():
        return {"status": "error", "error": "image_not_found"}
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
        return {"status": "not_a_floor_plan", "error": "unsupported_image_type"}
    try:
        from keprix.model_tools import _run_async
        from tools.vision_tools import vision_analyze_tool
        raw = _run_async(vision_analyze_tool(str(path), floor_plan_vision_prompt(mode), model))
        payload = json.loads(raw) if isinstance(raw, str) else raw
        analysis = str((payload or {}).get("analysis") or raw)
        if "not a floor plan" in analysis.lower():
            return {"status": "not_a_floor_plan", "analysis": analysis, "proposed_rooms": []}
        return {"status": "complete", "analysis": analysis, "proposed_rooms": parse_floor_plan_vision_proposal(analysis), "proposal_only": True}
    except Exception as exc:  # provider and parsing failures are explicit
        return {"status": "vision_unavailable", "error": f"{type(exc).__name__}: {exc}"}
