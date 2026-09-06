import sqlite3

from keprix.property_data.refresh import refresh_all
from keprix.property_data.saved_searches import create_saved_search, list_matches, propose_handoff, run_saved_search, update_match_status


def test_saved_search_rerun_is_idempotent_and_dismissed_match_is_not_reproposed(tmp_path):
    connection = sqlite3.connect(tmp_path / "property.sqlite")
    refresh_all(
        connection,
        ppd_rows=[
            {"transaction_id": "a", "uprn": "u1", "address_full": "1 Test Street", "postcode": "PO1", "price_gbp": "100000", "sale_date": "2010-01-01"},
            {"transaction_id": "b", "uprn": "u1", "address_full": "1 Test Street", "postcode": "PO1", "price_gbp": "110000", "sale_date": "2011-01-01"},
        ],
    )
    search = create_saved_search("ws1", "Old properties", {"min_score": 0.1}, connection=connection)
    first = run_saved_search(search["id"], "ws1", connection=connection)
    second = run_saved_search(search["id"], "ws1", connection=connection)
    assert len(first["matches"]) == 1
    assert len(second["matches"]) == 1
    assert connection.execute("SELECT COUNT(*) FROM property_saved_search_matches").fetchone()[0] == 1
    match_id = first["matches"][0]["id"]
    assert update_match_status(match_id, "ws1", "dismissed", connection=connection) is True
    assert list_matches(search["id"], "ws1", connection=connection)[0]["status"] == "dismissed"
    assert propose_handoff(match_id, "ws1", connection=connection)["status"] == "dismissed"
