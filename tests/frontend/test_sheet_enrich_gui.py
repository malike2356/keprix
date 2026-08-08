"""Frontend guards for sheet enrich GUI (prompts 477-478)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_crm_enrich_page_wires_sheet_api() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/crm/enrich/page.tsx").read_text(encoding="utf-8")
    assert "uploadCrmSheet" in page
    assert "proposeCrmSheet" in page
    assert "applyCrmSheetJob" in page
    assert "Soft Wall" in page or "soft wall" in page.lower()
    assert "column" in page.lower()


def test_sheet_api_client_and_nav() -> None:
    api = (ROOT / "frontend/src/lib/crm-api.ts").read_text(encoding="utf-8")
    assert "/api/crm/sheets/upload" in api
    assert "/api/crm/sheets/propose" in api
    py = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    ts = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert "/crm/enrich" in py and "crm-enrich" in py
    assert "/crm/enrich" in ts


def test_data_sheets_tab_redirects_to_enrich() -> None:
    client = (ROOT / "frontend/src/app/(workspace)/data/DataWorkspaceClient.tsx").read_text(
        encoding="utf-8"
    )
    assert '=== "sheets"' in client or "== \"sheets\"" in client or "sheets" in client
    assert "/crm/enrich" in client


def test_soft_wall_kind_sheet_preprocess_apply() -> None:
    routes = (ROOT / "src/keprix/sheet_preprocess/routes.py").read_text(encoding="utf-8")
    assert "sheet.preprocess.apply" in routes
    soft = (ROOT / "src/keprix/crm/soft_wall.py").read_text(encoding="utf-8")
    assert "sheet.preprocess.apply" in soft
