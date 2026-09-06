"""Public wrapper for the deterministic, data-backed floor-plan checks."""

from keprix.property_calculators.floor_plan_compliance import compliance_report


def check(rooms: list[dict], property_type: str = "hmo", region: str = "england") -> dict:
    return compliance_report(rooms, property_type=property_type, region=region)
