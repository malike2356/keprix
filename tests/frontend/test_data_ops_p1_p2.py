"""Frontend guards for local models + video ingest data-ops Must."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_local_models_page_must_haves() -> None:
    page = (ROOT / "frontend/src/components/data/panels/LocalModelsPanel.tsx").read_text(encoding="utf-8")
    data_page = (ROOT / "frontend/src/app/(workspace)/data/DataWorkspaceClient.tsx").read_text(encoding="utf-8")
    api = (ROOT / "frontend/src/lib/playbook-api.ts").read_text(encoding="utf-8")
    routes = (ROOT / "src/keprix/playbook/routes.py").read_text(encoding="utf-8")
    assert "Looking for Playbooks" in page
    assert "/playbooks" in page
    assert "watchModelDownload" in page or "watchModelDownload" in api
    assert "Use in chat" in page
    assert "Serving inventory" in page
    assert "LocalModelsPanel" in data_page
    assert "DataSectionTabs" in data_page
    assert "serving/health" in routes
    assert "stopModel" in api


def test_video_ingest_page_must_haves() -> None:
    page = (ROOT / "frontend/src/components/data/panels/VideoIngestPanel.tsx").read_text(encoding="utf-8")
    data_page = (ROOT / "frontend/src/app/(workspace)/data/DataWorkspaceClient.tsx").read_text(encoding="utf-8")
    routes = (ROOT / "src/keprix/api/video_ingest_routes.py").read_text(encoding="utf-8")
    assert "VideoIngestPanel" in data_page
    assert "DataSectionTabs" in data_page
    assert "Frame strip" in page
    assert "Open in chat" in page
    assert "caption-only" in page
    assert "refreshInterval" in page
    assert "Job detail" in page or "job detail" in page.lower()
    assert "/upload" in routes
    assert "frames/{index}" in routes or "frames/{index}" in routes
