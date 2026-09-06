from __future__ import annotations

from keprix.property_floorplan.compliance import check
from keprix.property_calculators.floor_plan_compliance import refurb_technical_considerations


def test_england_rules_are_versioned_and_failures_have_specific_rule_ids() -> None:
    report = check(
        [
            {"label": "Bedroom 1", "floor_area_sqm": 5.0, "occupancy_type": "single"},
            {"label": "Bedroom 2", "floor_area_sqm": 7.0, "occupancy_type": "single"},
        ],
        region="england",
    )

    assert report["rules_version"] == "2026-09-01"
    assert report["computed_checks"]["all_pass"] is False
    failed = report["computed_checks"]["rooms_checked"][0]
    assert failed["rule_id"] == "hmo.room_size.single.minimum"
    assert failed["status"] == "fail"


def test_unsupported_region_fails_closed() -> None:
    report = check(
        [{"label": "Bedroom", "floor_area_sqm": 20, "occupancy_type": "double"}],
        region="unknown-region",
    )

    assert report["computed_checks"]["status"] == "unsupported_region"
    assert report["computed_checks"]["all_pass"] is None


def test_refurb_guidance_cites_the_loaded_compliance_rule() -> None:
    items = refurb_technical_considerations(
        [{"label": "Bedroom", "floor_area_sqm": 5, "occupancy_type": "single"}],
    )

    room_item = next(item for item in items if item["category"] == "hmo_licensing")
    assert room_item["rule_id"] == "hmo.room_size.single.minimum"
    assert room_item["source"].startswith("Housing Act 2004")
