"""Support incident tests."""

from __future__ import annotations

from keprix.support.incidents import add_incident_update, create_incident, generate_public_incident_post


def test_incident_post_can_be_generated() -> None:
    incident = create_incident(
        title="API latency",
        severity="medium",
        summary="Elevated response times on workspace API.",
    )
    add_incident_update(incident["id"], message="Investigating database pool saturation.", status="investigating")
    updated = add_incident_update(incident["id"], message="Pool size increased.", status="resolved")
    assert updated is not None
    post = generate_public_incident_post(updated)
    assert "API latency" in post
    assert "Investigating database pool saturation" in post
    assert "Resolved:" in post
    assert "do not include customer data or secrets" in post
