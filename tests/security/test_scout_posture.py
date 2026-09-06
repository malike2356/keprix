from keprix.security.scout_posture import compute_posture


def test_green_posture_is_strong():
    result = compute_posture({})
    assert result["score"] == 100
    assert result["grade"] == "strong"
    assert result["findings"] == []


def test_failing_posture_is_explainable():
    result = compute_posture({"failed_logins": 10, "egress_anomalies": 4, "open_incidents": 2})
    assert result["grade"] in {"poor", "critical"}
    assert {finding["category"] for finding in result["findings"]} == {"authentication", "egress", "incidents"}
