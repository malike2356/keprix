"""Public wrapper for deterministic refurbishment guidance."""

from keprix.property_calculators.floor_plan_compliance import refurb_technical_considerations


def guidance(rooms: list[dict], property_type: str = "hmo") -> list[dict]:
    return refurb_technical_considerations(rooms, property_type=property_type)
