import sqlite3

from keprix.property_data.routes import router
from keprix.property_data.discovery import discover, set_config
from keprix.property_data.refresh import refresh_all


def test_discovery_ranks_signals_and_honours_toggle(tmp_path):
    connection = sqlite3.connect(tmp_path / "property.sqlite")
    refresh_all(
        connection,
        ppd_rows=[
            {"transaction_id": "a", "uprn": "strong", "address_full": "1 High Street", "postcode": "PO1", "price_gbp": "100000", "sale_date": "2010-01-01"},
            {"transaction_id": "b", "uprn": "strong", "address_full": "1 High Street", "postcode": "PO1", "price_gbp": "110000", "sale_date": "2011-01-01"},
        ],
    )
    set_config("ws", {"min_score": 0.1}, connection)
    result = discover("ws", connection=connection)
    assert result["candidates"][0]["uprn"] == "strong"
    assert result["candidates"][0]["score"] > 0
    set_config("ws", {"enabled_signals": ["below_market"], "min_score": 0.1}, connection)
    assert discover("ws", connection=connection)["candidates"] == []


def test_discovery_without_owned_data_is_empty(tmp_path):
    connection = sqlite3.connect(tmp_path / "property.sqlite")
    assert discover("empty", connection=connection)["candidates"] == []


def test_property_route_contracts_are_versioned_and_separate():
    paths = {route.path for route in router.routes}
    assert "/api/property/data-layer/status" in paths
    assert "/api/property/data-layer/refresh" in paths
    assert "/api/property/discovery/config" in paths
    assert "/api/property/discover" in paths
