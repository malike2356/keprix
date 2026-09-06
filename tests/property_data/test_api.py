import sqlite3

import pytest

from keprix.property_data.api import lookup, sold_prices
from keprix.property_data.billing import meter_property_api_call
from keprix.property_data.billing import require_property_entitlement, workspace_property_entitlement
from keprix.property_data.refresh import refresh_all
from keprix.property_data.schema import ensure_schema
from keprix.billing.wallet.store import AiCreditStore, reset_ai_credit_store_for_tests


def test_derived_api_never_returns_raw_sale_rows(tmp_path):
    connection = sqlite3.connect(tmp_path / "property.sqlite")
    refresh_all(connection, ppd_rows=[{"transaction_id": "tx1", "uprn": "u1", "address_full": "1 Test Street", "postcode": "PO1", "price_gbp": "100000", "sale_date": "2020-01-01"}])
    result = sold_prices(postcode="PO1", connection=connection)
    assert result["count"] == 1
    assert result["mean_price_gbp"] == 100000
    assert "transaction_id" not in result
    assert connection.execute("SELECT COUNT(*) FROM property_api_calls").fetchone()[0] == 1


def test_lookup_includes_attribution_and_derived_signals(tmp_path):
    connection = sqlite3.connect(tmp_path / "property.sqlite")
    refresh_all(connection, ppd_rows=[{"transaction_id": "tx1", "uprn": "u1", "address_full": "1 Test Street", "postcode": "PO1", "price_gbp": "100000", "sale_date": "2020-01-01"}])
    result = lookup(uprn="u1", workspace_id="ws1", key_id="key1", connection=connection)
    assert result["found"] is True
    assert result["uprn"] == "u1"
    assert result["source"]
    assert connection.execute("SELECT workspace_id,key_id,endpoint FROM property_api_calls").fetchone() == ("ws1", "key1", "lookup")


def test_property_meter_is_idempotent_and_records_workspace_ledger(tmp_path):
    connection = sqlite3.connect(tmp_path / "property.sqlite")
    reset_ai_credit_store_for_tests(AiCreditStore(tmp_path / "wallet.sqlite"))

    first = meter_property_api_call(
        workspace_id="ws1",
        endpoint="lookup",
        connection=connection,
        idempotency_key="retry-1",
    )
    second = meter_property_api_call(
        workspace_id="ws1",
        endpoint="lookup",
        connection=connection,
        idempotency_key="retry-1",
    )

    assert first["idempotent"] is False
    assert second["idempotent"] is True
    assert connection.execute("SELECT COUNT(*) FROM property_api_calls").fetchone()[0] == 1
    entries = reset_ai_credit_store_for_tests(AiCreditStore(tmp_path / "wallet.sqlite")).list_ledger("ws1")
    assert len(entries) == 1
    assert entries[0].metadata["idempotency_key"] == "retry-1"


def test_property_meter_failure_is_non_fatal(monkeypatch, tmp_path):
    connection = sqlite3.connect(tmp_path / "property.sqlite")
    refresh_all(connection, ppd_rows=[{"transaction_id": "tx1", "uprn": "u1", "address_full": "1 Test Street", "postcode": "PO1", "price_gbp": "100000", "sale_date": "2020-01-01"}])

    def fail(*args, **kwargs):
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr("keprix.billing.wallet.store.get_ai_credit_store", fail)
    result = lookup(uprn="u1", workspace_id="ws1", connection=connection)

    assert result["found"] is True
    assert connection.execute("SELECT COUNT(*) FROM property_api_calls").fetchone()[0] == 1


def test_schema_migrates_existing_property_api_calls_table(tmp_path):
    connection = sqlite3.connect(tmp_path / "property.sqlite")
    connection.execute("CREATE TABLE property_api_calls (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, key_id TEXT NOT NULL DEFAULT '', endpoint TEXT NOT NULL, uprn TEXT NOT NULL DEFAULT '', postcode TEXT NOT NULL DEFAULT '', cost_tokens REAL NOT NULL DEFAULT 0, called_at TEXT NOT NULL)")
    connection.commit()

    ensure_schema(connection)

    columns = {row[1] for row in connection.execute("PRAGMA table_info(property_api_calls)").fetchall()}
    assert "idempotency_key" in columns


def test_property_entitlement_denies_below_tier_and_allows_grandfather(monkeypatch, tmp_path):
    monkeypatch.setenv("KEPRIX_BILLING_ENABLED", "1")
    monkeypatch.setenv("KEPRIX_PROPERTY_CURRENT_TIER", "community")
    monkeypatch.setenv("KEPRIX_PROPERTY_REQUIRED_TIER", "full")
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))

    assert workspace_property_entitlement("ws1")["included"] is False
    with pytest.raises(Exception) as denied:
        require_property_entitlement("ws1")
    assert denied.value.status_code == 402

    (tmp_path / "billing").mkdir(exist_ok=True)
    (tmp_path / "billing" / "property-grandfathering.json").write_text("[\"ws1\"]", encoding="utf-8")
    assert require_property_entitlement("ws1")["grandfathered"] is True
