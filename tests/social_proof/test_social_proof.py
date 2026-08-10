"""Social proof collect → curate → publish tests."""

from __future__ import annotations

from pathlib import Path

from keprix.social_proof import (
    ProofTestimonialStore,
    approve,
    collect_primary,
    curate_top,
    reset_weekly_for_tests,
    run_weekly,
)

FIXTURES = Path(__file__).resolve().parents[2] / "src" / "keprix" / "social_proof" / "fixtures" / "sample-collect.json"


def test_collect_three_platforms_approve_and_list(tmp_path):
    reset_weekly_for_tests()
    store = ProofTestimonialStore(str(tmp_path / "t.json"))
    results = collect_primary(store, fixtures_path=str(FIXTURES), product="keprix")
    assert len(results) == 3
    assert sum(r["added"] for r in results) >= 3
    pending = store.list(status="pending")
    for row in pending[:3]:
        approve(store, row["id"])
    approved = store.list(status="approved")
    assert len(approved) == 3
    top = curate_top(approved, "all", 10)
    assert len(top) == 3
    assert all(r.get("url") for r in approved)


def test_weekly_schedule_and_manual_url_required(tmp_path):
    reset_weekly_for_tests()
    store = ProofTestimonialStore(str(tmp_path / "t2.json"))
    try:
        store.upsert({"text": "x", "author": "a", "url": ""})
        raised = False
    except ValueError:
        raised = True
    assert raised is True
    first = run_weekly(store, fixtures_path=str(FIXTURES), force=True)
    assert first["ran"] is True
    second = run_weekly(store, fixtures_path=str(FIXTURES), force=False)
    assert second["ran"] is False
