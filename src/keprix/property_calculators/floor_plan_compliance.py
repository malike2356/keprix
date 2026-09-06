"""Floor plan compliance checking (engine prompt 155) - the genuinely
deterministic half of the feature.

Real finding that corrects prompt 155's own assumption: Propreneur's
actual FloorPlanComplianceAdvisor.php is NOT a declarative ruleset - it
is itself an LLM prompt call (routeRequest() with a `compliance_advisory_
layer` prompt template, parsing whatever JSON the model returns). So
"port the compliance ruleset natively" does not mean porting existing
deterministic logic - there isn't any to port. Instead, this module
builds a genuinely deterministic check from the same real regulatory
numbers already in constants.py (HMO_MIN_ROOM_SIZE_SQM_*, sourced from
config/property_constants.php's own comment: "Housing Act 2004" -
English HMO minimum room sizes are a real, fixed, published standard).
This is more trustworthy than reproducing an AI-prompted "advisor" that
could hallucinate a room-size threshold - wrong compliance advice has
real regulatory consequences (this file's own guiding constraint, taken
directly from prompt 155's pitfalls section).

Scope discipline (also from 155's own honest-complexity note): only room
size is checked here, because it is the one input in a room list that is
genuinely computable from geometry alone. Fire safety, means of escape,
and other real HMO licensing requirements are listed as informational
items that need a site inspection or a qualified assessor - never
computed as a pass/fail here, because doing so from a floor plan's
extracted room list alone would be fabricating a compliance verdict this
module cannot actually verify.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from keprix.property_calculators.constants import (
    HMO_MIN_ROOM_SIZE_SQM_CHILD,
    HMO_MIN_ROOM_SIZE_SQM_DOUBLE,
    HMO_MIN_ROOM_SIZE_SQM_SINGLE,
)

_RULES_DIR = Path(__file__).with_name("rules")


def _load_rules(region: str) -> dict[str, Any] | None:
    path = _RULES_DIR / f"{region.strip().lower()}_hmo.json"
    try:
        with path.open(encoding="utf-8") as handle:
            rules = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return rules if isinstance(rules, dict) else None

# The real integration shape with Hermes's own existing vision_analyze
# tool (tools/vision_tools.py) - deliberately NOT a server-side "upload
# an image, get JSON back" endpoint. vision_analyze loads an image into
# the model's own context for its next turn; it does not itself return
# structured data. So floor-plan extraction is a conversational,
# worker-driven flow: the worker calls vision_analyze with the image and
# this question, reads the model's own next-turn answer, and if it
# contains real room dimensions, the worker (or the user) passes them
# into check_hmo_room_sizes()/compliance_report() above - never a
# fabricated one-shot "analyze this image" call this module cannot
# actually make happen synchronously.
FLOOR_PLAN_EXTRACTION_QUESTION = (
    "This is a floor plan. List every room you can identify with a label "
    "(e.g. 'Bedroom 1', 'Kitchen'), its approximate floor area in square "
    "metres if dimensions or a scale are visible (or state 'not "
    "determinable from this image' if they are not), and whether it "
    "looks like a bedroom intended for single or double occupancy. "
    "Reply with a real, honest reading of what's actually shown - if "
    "dimensions are not legible or no scale is given, say so rather than "
    "guessing a number."
)

# Same trust model as FLOOR_PLAN_EXTRACTION_QUESTION: vision proposes
# observations for the user to confirm in the Floor Plan form - never
# auto-submitted as ground truth to calculators that produce money figures.
FLOOR_PLAN_BOQ_EXTRACTION_QUESTION = (
    "This is a floor plan. List every room you can identify with a label "
    "(e.g. 'Bedroom 1', 'Kitchen'), its approximate floor area in square "
    "metres if dimensions or a scale are visible (or state 'not "
    "determinable from this image' if they are not), and whether it "
    "looks like a bedroom intended for single or double occupancy. "
    "For each room, also describe visible condition and any likely refurb "
    "work as plain-language observations to confirm (e.g. 'flooring looks "
    "worn - may need replacing') - frame these as observations the user "
    "must verify, never as committed scope items. "
    "Reply with a real, honest reading of what's actually shown - if "
    "dimensions are not legible or no scale is given, say so rather than "
    "guessing a number."
)

# Appended when vision runs from the Floor Plan upload endpoint so the
# frontend can pre-fill the confirmation form. Still proposal-only: the
# user must review before any calculator runs.
FLOOR_PLAN_VISION_JSON_SUFFIX = (
    "\n\nAfter your narrative, if you can honestly identify rooms, append a fenced JSON block "
    'with the label floor_plan_proposal and shape {"rooms":[{"label":"Bedroom 1",'
    '"floor_area_sqm":null,"occupancy_type":"single","room_type":"bedroom",'
    '"scope_observations":["flooring looks worn - may need replacing"]}]}. '
    "Use null for any value you cannot determine from the image; never guess numbers."
)

_SCOPE_OBSERVATION_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("repaint", ("repaint", "redecorate", "re-decorat", "paint", "decorat")),
    ("reflooring", ("refloor", "flooring", "floor", "carpet", "laminate", "vinyl", "tile")),
    ("replaster", ("replaster", "plaster", "skim", "render")),
    ("rewire", ("rewire", "electrical", "wiring", "socket")),
    ("new_kitchen_fit_out", ("kitchen fit", "new kitchen", "kitchen refurb", "kitchen replacement")),
    ("new_bathroom_fit_out", ("bathroom fit", "new bathroom", "bathroom refurb", "bathroom replacement")),
)

_VALID_OCCUPANCY = frozenset({"single", "double", "child_under_10"})
_VALID_ROOM_TYPES = frozenset({"bedroom", "bathroom", "kitchen", "reception", "hallway", "other"})

def _room_area_sqm(room: dict[str, Any]) -> float | None:
    if room.get("floor_area_sqm") is not None:
        try:
            return float(room["floor_area_sqm"])
        except (TypeError, ValueError):
            return None
    width = room.get("width_m")
    length = room.get("length_m")
    if width is not None and length is not None:
        try:
            return round(float(width) * float(length), 2)
        except (TypeError, ValueError):
            return None
    return None


def check_hmo_room_sizes(rooms: list[dict[str, Any]], region: str = "england") -> dict[str, Any]:
    """Real, deterministic check against Housing Act 2004 HMO minimum
    room sizes. Each room needs: `label`, either `floor_area_sqm` or
    `width_m`+`length_m`, and `occupancy_type` (single/double/
    child_under_10) - rooms not intended as a bedroom (kitchen, bathroom,
    hallway) should be omitted or given occupancy_type null, and are
    skipped here rather than incorrectly flagged."""
    rules = _load_rules(region)
    if rules is None:
        return {"region": region, "rules_source": None, "rooms_checked": [], "critical_count": 0, "all_pass": None, "status": "unsupported_region"}
    minimums = rules.get("bedroom_minimums_sqm", {})
    results = []
    critical_count = 0
    for room in rooms:
        occupancy = room.get("occupancy_type")
        if not occupancy:
            continue
        minimum = minimums.get(str(occupancy))
        if minimum is None:
            results.append(
                {
                    "room": room.get("label", "Unnamed room"),
                    "occupancy_type": occupancy,
                    "status": "unknown_occupancy_type",
                    "message": f"'{occupancy}' is not a recognised occupancy type (single/double/child_under_10) - skipped.",
                }
            )
            continue
        area = _room_area_sqm(room)
        if area is None:
            results.append(
                {
                    "room": room.get("label", "Unnamed room"),
                    "occupancy_type": occupancy,
                    "status": "insufficient_data",
                    "message": "No floor_area_sqm or width_m/length_m provided - cannot check.",
                }
            )
            continue
        passes = area >= minimum
        if not passes:
            critical_count += 1
        results.append(
            {
                "room": room.get("label", "Unnamed room"),
                "rule_id": f"hmo.room_size.{occupancy}.minimum",
                "occupancy_type": occupancy,
                "area_sqm": area,
                "minimum_required_sqm": minimum,
                "status": "pass" if passes else "fail",
                "message": (
                    f"{area} sqm meets the {minimum} sqm minimum for {occupancy.replace('_', ' ')} occupancy."
                    if passes
                    else f"{area} sqm is below the {minimum} sqm minimum for {occupancy.replace('_', ' ')} occupancy - not licensable as configured."
                ),
            }
        )

    return {
        "region": region,
        "rules_version": rules.get("version"),
        "rules_source": rules.get("source"),
        "rooms_checked": results,
        "critical_count": critical_count,
        "all_pass": critical_count == 0 and len(results) > 0,
    }


def compliance_report(rooms: list[dict[str, Any]], property_type: str = "hmo", region: str = "england") -> dict[str, Any]:
    """Full compliance report: real, computed room-size verdicts plus the
    informational items that genuinely need a site assessment. Never
    blends the two into one fabricated overall pass/fail - a workspace
    reading this must be able to tell computed fact from "still needs a
    human to check" at a glance."""
    rules = _load_rules(region)
    room_size_result = check_hmo_room_sizes(rooms, region=region) if property_type == "hmo" else {
        "rules_source": None,
        "rooms_checked": [],
        "critical_count": 0,
        "all_pass": None,
        "note": f"Room-size minimums in this module are HMO-specific; property_type '{property_type}' has no computed check here.",
    }

    return {
        "property_type": property_type,
        "computed_checks": room_size_result,
        "region": region,
        "rules_version": rules.get("version") if rules else None,
        "needs_site_assessment": rules.get("site_assessment", []) if rules else [],
        "assumptions": [
            "Room size thresholds are loaded from the versioned jurisdiction rules file and are estimates requiring local-authority confirmation.",
            "Only room size is computed here - it is the one input derivable from geometry alone.",
            "Fire safety, means of escape, smoke alarms, and kitchen adequacy always need a real site assessment - never computed as pass/fail from a floor plan alone.",
            "Local authorities can set additional/stricter HMO standards beyond the national minimums - always confirm with the specific licensing authority.",
        ],
    }


# Deterministic refurb sequencing / building-regs flags keyed on scope-of-
# works combinations. Omit uncertain rules rather than guess - shorter and
# correct beats longer and unreliable (same discipline as room-size checks).
_REFURB_TECHNICAL_RULES: list[dict[str, Any]] = [
    {
        "id": "sequencing.rewire+replaster",
        "requires_all": {"rewire", "replaster"},
        "category": "sequencing",
        "label": "Electrical before plastering",
        "message": "Complete electrical first-fix and test before plastering to avoid re-opening finished walls.",
        "source": "UK trade sequencing practice (first-fix before wet trades)",
    },
    {
        "id": "sequencing.rewire+repaint",
        "requires_all": {"rewire", "repaint"},
        "category": "sequencing",
        "label": "Rewire before decoration",
        "message": "Finish rewiring and obtain electrical certification before final decoration.",
        "source": "UK trade sequencing practice",
    },
    {
        "id": "sequencing.replaster+repaint",
        "requires_all": {"replaster", "repaint"},
        "category": "sequencing",
        "label": "Plaster drying before paint",
        "message": "Allow new plaster to dry fully (typically several weeks depending on depth and ventilation) before final decoration.",
        "source": "UK trade sequencing practice",
    },
    {
        "id": "sequencing.replaster+reflooring",
        "requires_all": {"replaster", "reflooring"},
        "category": "sequencing",
        "label": "Plaster before flooring",
        "message": "Complete plastering and drying at wall edges before installing new flooring.",
        "source": "UK trade sequencing practice",
    },
    {
        "id": "preparation.reflooring.damp",
        "requires_any": {"reflooring"},
        "category": "preparation",
        "label": "Subfloor damp check",
        "message": "Check subfloor moisture content and level before laying new flooring.",
        "source": "UK flooring trade practice",
    },
    {
        "id": "regs.part_p.rewire",
        "requires_any": {"rewire"},
        "category": "building_regs",
        "label": "Part P (electrical safety)",
        "message": "Rewiring is notifiable work in England and Wales under Part P - use a registered competent person or notify building control.",
        "source": "Building Regulations Part P (electrical safety)",
    },
    {
        "id": "regs.part_p.kitchen_fitout",
        "requires_any": {"new_kitchen_fit_out"},
        "category": "building_regs",
        "label": "Kitchen electrical/plumbing notifiable work",
        "message": "New kitchen circuits and altered plumbing may require Part P notification and compliance with water supply regulations - confirm scope with qualified trades.",
        "source": "Building Regulations Part P; Water Supply (Water Fittings) Regulations",
    },
    {
        "id": "regs.part_p.bathroom_fitout",
        "requires_any": {"new_bathroom_fit_out"},
        "category": "building_regs",
        "label": "Bathroom electrical/plumbing notifiable work",
        "message": "New bathroom circuits and altered plumbing are notifiable under Part P in wet zones - use qualified trades and confirm notification requirements.",
        "source": "Building Regulations Part P (bathroom zones)",
    },
]


def _scope_union(rooms: list[dict[str, Any]]) -> set[str]:
    items: set[str] = set()
    for room in rooms:
        for entry in room.get("scope") or []:
            text = str(entry).strip()
            if text:
                items.add(text)
    return items


def _rule_matches(rule: dict[str, Any], scope_items: set[str]) -> bool:
    requires_all = rule.get("requires_all")
    requires_any = rule.get("requires_any")
    if requires_all and not requires_all.issubset(scope_items):
        return False
    if requires_any and not (requires_any & scope_items):
        return False
    return True


def refurb_technical_considerations(rooms: list[dict[str, Any]], property_type: str = "hmo") -> list[dict[str, Any]]:
    """Deterministic refurb guidance keyed on confirmed scope-of-works.

    Same input always produces the same output. HMO licensing knowledge is
    reused from compliance_report()/check_hmo_room_sizes() - never
    re-derived here."""
    scope_items = _scope_union(rooms)
    considerations: list[dict[str, Any]] = []

    for rule in _REFURB_TECHNICAL_RULES:
        if _rule_matches(rule, scope_items):
            considerations.append(
                {
                    "key": rule["id"],
                    "category": rule["category"],
                    "label": rule["label"],
                    "message": rule["message"],
                    "rule_id": rule["id"],
                    "source": rule["source"],
                }
            )

    if property_type == "hmo":
        hmo_report = compliance_report(rooms, property_type="hmo")
        for checked in hmo_report["computed_checks"]["rooms_checked"]:
            if checked.get("status") == "fail":
                considerations.append(
                    {
                        "key": f"hmo.room_size.{checked['room']}",
                        "category": "hmo_licensing",
                        "label": "HMO minimum room size",
                        "message": checked["message"],
                        "rule_id": checked.get("rule_id", "hmo.room_size.fail"),
                        "source": hmo_report["computed_checks"]["rules_source"],
                    }
                )
        for item in hmo_report["needs_site_assessment"]:
            considerations.append(
                {
                    "key": f"hmo.{item['key']}",
                    "category": "hmo_site_assessment",
                    "label": item["label"],
                    "message": item["note"],
                    "rule_id": f"hmo.informational.{item['key']}",
                    "source": hmo_report["computed_checks"].get("rules_source"),
                }
            )

    return sorted(considerations, key=lambda row: str(row["rule_id"]))


def _extract_json_block(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    patterns = (
        r"```(?:json|floor_plan_proposal)\s*([\s\S]*?)```",
        r"(\{\s*\"rooms\"\s*:\s*\[[\s\S]*?\]\s*\})",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            candidate = match.group(1).strip()
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and isinstance(parsed.get("rooms"), list):
                return parsed
    return None


def scope_hints_from_observations(observations: list[str] | None) -> list[str]:
    if not observations:
        return []
    joined = " ".join(str(item).lower() for item in observations if str(item).strip())
    if not joined:
        return []
    hints: list[str] = []
    for scope_id, keywords in _SCOPE_OBSERVATION_HINTS:
        if any(keyword in joined for keyword in keywords):
            hints.append(scope_id)
    return hints


def normalize_proposed_room(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    label = str(raw.get("label") or "").strip()
    if not label:
        return None
    entry: dict[str, Any] = {"label": label}
    area = raw.get("floor_area_sqm")
    if area is not None:
        try:
            area_value = float(area)
            if area_value > 0:
                entry["floor_area_sqm"] = area_value
        except (TypeError, ValueError):
            pass
    occupancy = str(raw.get("occupancy_type") or "").strip().lower()
    if occupancy in _VALID_OCCUPANCY:
        entry["occupancy_type"] = occupancy
    room_type = str(raw.get("room_type") or "").strip().lower()
    if room_type in _VALID_ROOM_TYPES:
        entry["room_type"] = room_type
    observations = raw.get("scope_observations")
    if isinstance(observations, list):
        scope = scope_hints_from_observations([str(item) for item in observations])
        if scope:
            entry["scope"] = scope
            entry["scope_observations"] = [str(item) for item in observations if str(item).strip()]
    return entry


def parse_floor_plan_vision_proposal(analysis: str) -> list[dict[str, Any]]:
    """Best-effort parse of a vision narrative into editable room proposals."""
    payload = _extract_json_block(analysis)
    if not payload:
        return []
    rooms: list[dict[str, Any]] = []
    for raw in payload.get("rooms") or []:
        if not isinstance(raw, dict):
            continue
        normalized = normalize_proposed_room(raw)
        if normalized:
            rooms.append(normalized)
    return rooms


def floor_plan_vision_prompt(mode: str) -> str:
    base = FLOOR_PLAN_BOQ_EXTRACTION_QUESTION if mode == "boq" else FLOOR_PLAN_EXTRACTION_QUESTION
    return f"{base}{FLOOR_PLAN_VISION_JSON_SUFFIX}"
