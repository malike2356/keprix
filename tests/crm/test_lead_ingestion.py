"""Canonical lead schema + spreadsheet ingestion (Prompt 621)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from keprix.crm.ingestion.canonical import (
    REFERENCE_HEADERS,
    map_headers,
    normalize_row,
)
from keprix.crm.ingestion.export import export_leads_csv, export_leads_xlsx
from keprix.crm.ingestion.readers import read_path, read_rows_list
from keprix.crm.ingestion.service import IngestOptions, ingest_file, ingest_row_array, ingest_rows
from keprix.crm.store import reset_crm_store_for_tests
from keprix.sheet_preprocess.safety import SheetLimits, SheetSafetyError

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SYNTHETIC_CSV = FIXTURES / "seo_lead_tracker_synthetic.csv"


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_schema_has_ingestion_columns(store) -> None:
    cols = store._columns("crm_leads")
    for name in (
        "website",
        "niche",
        "locality",
        "custom_fields",
        "source_type",
        "pipeline_stage",
        "merged_at",
    ):
        assert name in cols
    assert "crm_ingestion_jobs" in {
        r[0]
        for r in store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def test_synthetic_csv_round_trip_import_export(store, tmp_path: Path) -> None:
    result = ingest_file(
        "ws_a",
        SYNTHETIC_CSV,
        store=store,
        options=IngestOptions(source_name="synthetic.csv", actor_id="test"),
    )
    assert result["created"] == 2
    assert result["rejected"] == 0
    leads = store.list_leads("ws_a")
    assert len(leads) == 2
    by_email = {
        (lead.get("emails") or [{}])[0].get("address"): lead for lead in leads
    }
    ada = by_email["ada@acme-dental.example"]
    assert ada["company_name"] == "Acme Dental"
    assert ada["niche"] == "Dental"
    assert ada["locality"] == "Manchester"
    assert ada["website"] in {"acme-dental.example", "www.acme-dental.example"}
    assert ada["google_rating"] in {"4.6", "4.60"}
    assert ada["ranks_top3"] == "yes"
    assert ada["custom_fields"].get("Extra Column") == "keep-me"
    assert ada["source_job_id"] == result["job_id"]
    prov = store.list_provenance("ws_a", entity_type="lead", entity_id=ada["id"])
    assert prov

    xlsx_path = tmp_path / "out.xlsx"
    csv_path = tmp_path / "out.csv"
    export_leads_xlsx(leads, xlsx_path)
    export_leads_csv(leads, csv_path)
    assert xlsx_path.is_file()
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    exported = {r["Email"]: r for r in rows}
    assert exported["ada@acme-dental.example"]["Company"] == "Acme Dental"
    assert "keep-me" in exported["ada@acme-dental.example"]["Custom Fields"]


def test_alias_normalization_and_provenance(store) -> None:
    rows = [
        {
            "Organisation": "Gamma Ltd",
            "Town": "Bristol",
            "E-Mail": "gamma@example.com",
            "Telephone": "+44 117 555 0111",
            "Homepage": "https://WWW.Gamma.Example/path/",
            "Ranks Top 3": "true",
            "Date Added": "01/08/2026",
            "Mystery": "custom-val",
        }
    ]
    result = ingest_rows(
        "ws_a",
        rows,
        store=store,
        options=IngestOptions(source_type="api", source_name="alias-test"),
    )
    assert result["created"] == 1
    lead = store.get_lead("ws_a", result["created_ids"][0])
    assert lead["company_name"] == "Gamma Ltd"
    assert lead["locality"] == "Bristol"
    assert lead["emails"][0]["address"] == "gamma@example.com"
    assert lead["website"] == "gamma.example/path"
    assert lead["ranks_top3"] == "yes"
    assert lead["custom_fields"]["Mystery"] == "custom-val"
    assert lead["source_type"] == "api"
    assert store.list_provenance("ws_a", entity_type="lead", entity_id=lead["id"])


def test_dedup_merge_second_import(store) -> None:
    first = ingest_rows(
        "ws_a",
        [{"Company": "Acme", "Email": "a@example.com", "Niche": "Dental"}],
        store=store,
        options=IngestOptions(),
    )
    assert first["created"] == 1
    second = ingest_rows(
        "ws_a",
        [
            {
                "Company": "Acme",
                "Email": "a@example.com",
                "Phone": "+441615550100",
                "Town/City": "Manchester",
            }
        ],
        store=store,
        options=IngestOptions(overwrite=False),
    )
    assert second["created"] == 0
    assert second["updated"] == 1
    leads = store.list_leads("ws_a")
    assert len(leads) == 1
    lead = leads[0]
    assert lead["niche"] == "Dental"
    assert lead["locality"] == "Manchester"
    assert (lead.get("phones") or [{}])[0].get("number")


def test_csv_tsv_xlsx_required(store, tmp_path: Path) -> None:
    # CSV
    assert ingest_file("ws_a", SYNTHETIC_CSV, store=store)["created"] == 2
    store2 = reset_crm_store_for_tests(tmp_path / "crm2.sqlite")

    # TSV
    tsv = tmp_path / "leads.tsv"
    text = SYNTHETIC_CSV.read_text(encoding="utf-8")
    tsv.write_text(text.replace(",", "\t"), encoding="utf-8")
    assert ingest_file("ws_b", tsv, store=store2)["created"] == 2

    # XLSX via openpyxl
    openpyxl = pytest.importorskip("openpyxl")
    from openpyxl import Workbook

    store3 = reset_crm_store_for_tests(tmp_path / "crm3.sqlite")
    wb = Workbook()
    ws = wb.active
    with SYNTHETIC_CSV.open(encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            ws.append(row)
    xlsx = tmp_path / "leads.xlsx"
    wb.save(xlsx)
    assert ingest_file("ws_c", xlsx, store=store3)["created"] == 2


def test_ods_import(store, tmp_path: Path) -> None:
    pytest.importorskip("odf")
    import pandas as pd

    df = pd.read_csv(SYNTHETIC_CSV)
    ods = tmp_path / "leads.ods"
    df.to_excel(ods, index=False, engine="odf")
    assert ingest_file("ws_ods", ods, store=store)["created"] == 2


def test_xls_import(tmp_path: Path) -> None:
    pytest.importorskip("xlrd")
    pytest.importorskip("xlwt")
    import pandas as pd

    store = reset_crm_store_for_tests(tmp_path / "crm_xls.sqlite")
    df = pd.read_csv(SYNTHETIC_CSV)
    xls = tmp_path / "leads.xls"
    df.to_excel(xls, index=False, engine="xlwt")
    assert ingest_file("ws_xls", xls, store=store)["created"] == 2


def test_formula_kept_as_text_and_limits(store, tmp_path: Path) -> None:
    rows = [
        {
            "Company": "Formula Co",
            "Email": "f@example.com",
            "Notes": "=1+1",
        }
    ]
    result = ingest_rows("ws_a", rows, store=store, options=IngestOptions())
    assert result["created"] == 1
    lead = store.get_lead("ws_a", result["created_ids"][0])
    assert lead["notes"] == "=1+1"
    assert any("formula" in w.lower() for w in result["warnings"])

    rejected = ingest_rows(
        "ws_a",
        [{"Company": "Bad", "Email": "b@example.com", "Notes": "=CMD()"}],
        store=store,
        options=IngestOptions(reject_formula_fields=True),
    )
    assert rejected["rejected"] == 1

    with pytest.raises(SheetSafetyError):
        read_rows_list([{"c": "x"} for _ in range(10)], limits=SheetLimits(max_rows=5))

    with pytest.raises(SheetSafetyError):
        read_path(tmp_path / ".." / "etc" / "passwd")


def test_workspace_isolation(store) -> None:
    result = ingest_rows(
        "ws_a",
        [{"Company": "Only A", "Email": "onlya@example.com"}],
        store=store,
    )
    lead_id = result["created_ids"][0]
    assert store.get_lead("ws_b", lead_id) is None
    assert store.list_leads("ws_b") == []
    assert store.list_leads("ws_a")[0]["emails"][0]["address"] == "onlya@example.com"


def test_reference_headers_count_and_map() -> None:
    assert len(REFERENCE_HEADERS) == 17
    mapping = map_headers(list(REFERENCE_HEADERS))
    assert len(mapping) == 17
    normalized = normalize_row(
        {h: "x" for h in REFERENCE_HEADERS},
        header_map=mapping,
    )
    assert "company_name" in normalized
    assert "email" in normalized


def test_google_row_array_and_channel_bytes(store) -> None:
    rows = [
        {
            "Company": "Paste Co",
            "Email": "paste@example.com",
            "Town/City": "Leeds",
            "Custom Tag": "from-sheets",
        }
    ]
    pasted = ingest_row_array(
        "ws_a",
        rows,
        store=store,
        options=IngestOptions(source_type="google_sheet_rows", source_name="paste"),
    )
    assert pasted["created"] == 1
    lead = store.list_leads("ws_a")[0]
    assert (lead.get("custom_fields") or {}).get("Custom Tag") == "from-sheets"

    from keprix.crm.ingestion.service import ingest_channel_attachment

    csv_bytes = (
        "Company,Email\nChannel Co,channel@example.com\n"
    ).encode("utf-8")
    ch = ingest_channel_attachment(
        "ws_a",
        csv_bytes,
        filename="leads.csv",
        store=store,
        channel="telegram",
    )
    assert ch["created"] == 1
    assert ch.get("channel") == "telegram"
    assert any(
        (e.get("emails") or [{}])[0].get("address") == "channel@example.com"
        for e in store.list_leads("ws_a")
    )


def test_cli_preview_and_import(store, tmp_path: Path, monkeypatch) -> None:
    from keprix.crm.ingestion import __main__ as ingest_main

    monkeypatch.setenv("KEPRIX_CRM_DB_PATH", str(tmp_path / "cli_crm.sqlite"))
    reset_crm_store_for_tests(tmp_path / "cli_crm.sqlite")
    code = ingest_main.main(
        ["preview", str(SYNTHETIC_CSV), "--workspace-id", "ws_cli", "--limit", "2"]
    )
    assert code == 0
    code = ingest_main.main(
        ["import", str(SYNTHETIC_CSV), "--workspace-id", "ws_cli"]
    )
    assert code == 0


def test_phone_and_website_company_dedup(store) -> None:
    first = ingest_rows(
        "ws_a",
        [
            {
                "Company": "Web Co",
                "Website": "https://webco.example",
                "Town/City": "York",
                "Phone": "0161 555 9999",
            }
        ],
        store=store,
    )
    assert first["created"] == 1
    by_phone = ingest_rows(
        "ws_a",
        [{"Company": "Other", "Phone": "+4401615559999", "Email": "p@example.com"}],
        store=store,
    )
    assert by_phone["updated"] == 1 or by_phone["duplicate"] == 1 or by_phone["created"] == 0
    assert len(store.list_leads("ws_a")) == 1

    store2 = reset_crm_store_for_tests(store._path.parent / "crm_web.sqlite")
    ingest_rows(
        "ws_a",
        [{"Company": "Web Co", "Website": "webco.example", "Town/City": "York"}],
        store=store2,
    )
    second = ingest_rows(
        "ws_a",
        [
            {
                "Company": "Web Co",
                "Website": "https://www.webco.example",
                "Town/City": "York",
                "Niche": "SEO",
            }
        ],
        store=store2,
    )
    assert second["created"] == 0
    assert second["updated"] == 1
    assert store2.list_leads("ws_a")[0]["niche"] == "SEO"
