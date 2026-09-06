from keprix.property_data.ingest import ingest_ownership, ingest_uprn
from keprix.property_data.refresh import dataset_status, refresh_all


def test_property_refresh_is_idempotent_and_computes_signal(tmp_path):
    import sqlite3

    connection = sqlite3.connect(tmp_path / "property.sqlite")
    ppd = [
        {"transaction_id": "tx1", "uprn": "u1", "address_full": "1 Test Street", "postcode": "PO1", "price_gbp": "100000", "sale_date": "2010-01-01"},
        {"transaction_id": "tx2", "uprn": "u1", "address_full": "1 Test Street", "postcode": "PO1", "price_gbp": "110000", "sale_date": "2011-01-01"},
    ]
    first = refresh_all(connection, ppd_rows=ppd)
    second = refresh_all(connection, ppd_rows=ppd)
    assert first["sources"]["ppd"]["row_count"] == 2
    assert second["sources"]["ppd"]["row_count"] == 0
    assert dataset_status(connection)["counts"]["property_sold_prices"] == 2
    assert dataset_status(connection)["counts"]["property_signals"] == 1


def test_uprn_and_ownership_ingest_are_idempotent(tmp_path):
    import sqlite3

    connection = sqlite3.connect(tmp_path / "property.sqlite")
    assert ingest_uprn(connection, [{"UPRN": "u1", "ADDRESS": "1 Test Street", "POSTCODE": "PO1"}]) == 1
    assert ingest_uprn(connection, [{"UPRN": "u1", "ADDRESS": "1 Test Street", "POSTCODE": "PO1"}]) == 0
    assert ingest_ownership(connection, [{"UPRN": "u1", "Company Number": "0001", "Country": "GB"}]) == 1
    assert ingest_ownership(connection, [{"UPRN": "u1", "Company Number": "0001", "Country": "GB"}]) == 0
    assert dataset_status(connection)["counts"]["property_company_ownership"] == 1
