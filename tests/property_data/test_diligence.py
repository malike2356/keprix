import asyncio
import sqlite3

from keprix.property_data.diligence import run_due_diligence
from keprix.property_data.ingest import ingest_epc, ingest_ownership
from keprix.property_data.refresh import refresh_all


def test_due_diligence_returns_structured_available_and_unavailable_sections(tmp_path):
    connection = sqlite3.connect(tmp_path / "property.sqlite")
    refresh_all(connection, ppd_rows=[{"transaction_id": "tx1", "uprn": "u1", "address_full": "1 Test Street", "postcode": "PO1", "price_gbp": "100000", "sale_date": "2025-01-01"}])
    ingest_epc(connection, [{"certificate_id": "epc1", "uprn": "u1", "CURRENT_ENERGY_RATING": "C", "POTENTIAL_ENERGY_RATING": "B", "CURRENT_ENERGY_EFFICIENCY": "70", "TOTAL_FLOOR_AREA": "80"}])
    ingest_ownership(connection, [{"UPRN": "u1", "Company Number": "0001", "Country": "GB"}])
    report = asyncio.run(run_due_diligence("u1", connection=connection))
    assert report["sections"]["comparables"]["status"] == "available"
    assert report["sections"]["epc"]["current_rating"] == "C"
    assert report["sections"]["ownership"]["overseas_owner"] is True
    assert report["sections"]["companies_house"]["status"] == "unavailable"
    by_address = asyncio.run(run_due_diligence(address="1 Test Street", connection=connection))
    assert by_address["uprn"] == "u1"
