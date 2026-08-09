"""Frontend guards for user-selectable spreadsheet input and delivery formats."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_enrich_page_offers_google_sheet_import_and_delivery_choices() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/crm/enrich/page.tsx").read_text(encoding="utf-8")
    for label in (
        "Google Sheet URL or ID",
        "Import Google Sheet",
        "Download Excel",
        "Download CSV",
        "Create Google Sheet",
    ):
        assert label in page


def test_crm_api_supports_format_selection() -> None:
    api = (ROOT / "frontend/src/lib/crm-api.ts").read_text(encoding="utf-8")
    assert 'format: "xlsx" | "csv" = "xlsx"' in api
    assert "importCrmGoogleSheet" in api
    assert "publishCrmGoogleSheet" in api
