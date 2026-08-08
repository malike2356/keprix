"""Frontend guards for fleet, companion, data plane, jobs, ML, export (482-487)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_fleet_admin_gui_and_nav() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/admin/fleet/page.tsx").read_text(encoding="utf-8")
    api = (ROOT / "frontend/src/lib/fleet-api.ts").read_text(encoding="utf-8")
    assert "/admin/fleet" in page or "Fleet" in page
    assert "fleet_deploy" in page
    assert "Enterprise feature" in page or "Enterprise Edition" in page
    assert "/api/fleet/instances" in api
    assert "/probe" in api
    py = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    ts = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert "admin-fleet" in py and 'href: "/admin/fleet"' in ts
    doc = (ROOT / "docs/operations/fleet.md").read_text(encoding="utf-8")
    assert "/admin/fleet" in doc


def test_companion_pairing_gui_and_docs() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/admin/companion/page.tsx").read_text(encoding="utf-8")
    api = (ROOT / "frontend/src/lib/companion-api.ts").read_text(encoding="utf-8")
    assert "Create pair session" in page
    assert "/api/companion/pair" in api
    assert "revoke" in page.lower()
    mobile = (ROOT / "docs/integrations/mobile.md").read_text(encoding="utf-8")
    assert "/admin/companion" in mobile
    assert "primary operator path" in mobile.lower() or "GUI is the primary" in mobile
    py = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    assert "admin-companion" in py


def test_data_plane_and_jobs_tabs() -> None:
    tabs = (ROOT / "frontend/src/components/data/DataSectionTabs.tsx").read_text(encoding="utf-8")
    client = (ROOT / "frontend/src/app/(workspace)/data/DataWorkspaceClient.tsx").read_text(
        encoding="utf-8"
    )
    assert '"datasets"' in tabs or "value: \"datasets\"" in tabs
    assert '"jobs"' in tabs or "value: \"jobs\"" in tabs
    assert '"ml"' in tabs or "value: \"ml\"" in tabs
    assert '"export"' in tabs or "value: \"export\"" in tabs
    assert "DatasetsPanel" in client
    assert "JobsQueuePanel" in client
    assert "MlWorkspacePanel" in client
    assert "DocumentExportPanel" in client
    data_api = (ROOT / "frontend/src/lib/data-plane-api.ts").read_text(encoding="utf-8")
    jobs_api = (ROOT / "frontend/src/lib/jobs-api.ts").read_text(encoding="utf-8")
    assert "/api/data/catalog" in data_api
    assert "/api/jobs" in jobs_api
    assert "/cancel" in jobs_api and "/retry" in jobs_api
    docs = (ROOT / "docs/operations/data-planes.md").read_text(encoding="utf-8")
    assert "/data?tab=datasets" in docs
    assert "/data?tab=jobs" in docs


def test_ml_and_export_clients() -> None:
    ml = (ROOT / "frontend/src/lib/ml-api.ts").read_text(encoding="utf-8")
    export_api = (ROOT / "frontend/src/lib/document-export-api.ts").read_text(encoding="utf-8")
    panel = (ROOT / "frontend/src/components/data/panels/DocumentExportPanel.tsx").read_text(
        encoding="utf-8"
    )
    assert "/api/ml/experiments" in ml
    assert "/api/export" in export_api
    assert "Soft Wall" in panel or "Restricted classification" in panel
    docs_page = (ROOT / "frontend/src/app/(workspace)/documents/page.tsx").read_text(encoding="utf-8")
    assert "/data?tab=export" in docs_page


def test_fleet_remove_and_jobs_cancel_routes_exist() -> None:
    fleet = (ROOT / "src/keprix/fleet/routes.py").read_text(encoding="utf-8")
    jobs = (ROOT / "src/keprix/jobs/routes.py").read_text(encoding="utf-8")
    assert "remove_instance" in fleet or "/instances/{instance_id}" in fleet
    assert "probe_instance" in fleet
    assert "cancel_job" in jobs and "retry_job" in jobs
