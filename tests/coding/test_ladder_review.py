from keprix.coding.ladder_review import review_diff


def test_ladder_review_flags_future_proofing() -> None:
    result = review_diff("+# TODO later future-proof this abstraction")

    assert result["findings"][0]["tag"] == "yagni"
