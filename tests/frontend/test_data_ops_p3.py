"""Frontend guards for data-ops P3 RAG Must surface."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_rag_panel_has_pipeline_list_and_split_tabs() -> None:
    panel = (ROOT / "frontend/src/components/data/panels/RagPipelinePanel.tsx").read_text(encoding="utf-8")
    assert "Known pipelines" in panel
    assert "fetchRagConfig" in panel
    assert 'mode="run"' in panel
    assert 'mode="history"' in panel
    assert "keprix_rag_replay_question" in panel
    data_page = (ROOT / "frontend/src/app/(workspace)/data/DataWorkspaceClient.tsx").read_text(encoding="utf-8")
    assert "RagPipelinePanel" in data_page
    assert "DataSectionTabs" in data_page


def test_rag_run_viewer_timeline_citations_replay() -> None:
    viewer = (ROOT / "frontend/src/components/rag/PipelineRunViewer.tsx").read_text(encoding="utf-8")
    assert "Step timeline" in viewer
    assert 'splitter: "chunk"' in viewer
    assert "playbook_node" in viewer
    assert "runQuestion" in viewer
    assert "Citation preview" in viewer
    assert "Filter runs" in viewer
    assert "Re-run" in viewer
    assert "loadingHistory" in viewer


def test_rag_api_client_avoids_silent_hardcoded_defaults() -> None:
    api = (ROOT / "frontend/src/lib/rag-pipeline-api.ts").read_text(encoding="utf-8")
    assert "query?: string" in api
    assert 'pipeline_id: payload.pipeline_id || "production-default"' not in api
    assert 'form.append("pipeline_id", payload.pipeline_id || "production-default")' not in api
    assert "store_kind: \"memory\"" not in api or "if (payload.store_kind)" in api


def test_rag_builder_sources_and_store_run_labels() -> None:
    builder = (ROOT / "frontend/src/components/rag/PipelineBuilder.tsx").read_text(encoding="utf-8")
    assert 'value="manual"' in builder
    assert 'value="notion"' in builder
    assert 'value="file"' in builder
    assert 'value="vault"' in builder
    assert 'value="url"' in builder
    assert "runs)" in builder
    assert "knownPipelines" in builder


def test_stores_endpoint_labels_run_counts() -> None:
    routes = (ROOT / "src/keprix/rag_pipeline/routes.py").read_text(encoding="utf-8")
    assert '"count_label": "runs"' in routes
