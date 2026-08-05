"""Prompt 269 Graphiti ingest service tests."""

from __future__ import annotations

from pathlib import Path

from keprix.brain.graphiti_ingest_service import GraphitiIngestService
from keprix.brain.graphiti_job_store import GraphitiJobStore


class MockBridge:
    def __init__(self) -> None:
        self.episodes: list[dict] = []

    def add_episode(self, *, name: str, content: str, source_ref: str) -> dict:
        self.episodes.append({"name": name, "content": content, "source_ref": source_ref})
        return {"episode_id": "ep-1", "nodes_added": 2, "edges_added": 1}

    def query(self, query: str, *, max_results: int, include_sources: bool) -> dict:
        return {"hits": [{"fact": query, "source": "mock"}]}


def test_ingest_markdown_report_records_counts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("GRAPHITI_MCP_URL", "http://graphiti.test/mcp")
    report = tmp_path / "report.md"
    report.write_text("# Report\n\nCompetitor X ships faster.", encoding="utf-8")
    bridge = MockBridge()

    job = GraphitiIngestService(bridge=bridge).ingest(source_type="research", source_ref=str(report))

    assert job.status == "done"
    assert job.nodes_added == 2
    assert job.edges_added == 1
    assert bridge.episodes[0]["content"].startswith("# Report")
    assert GraphitiJobStore().get(job.job_id) is not None


def test_query_degrades_when_disabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_GRAPHITI_ENABLED", "0")

    result = GraphitiIngestService(bridge=MockBridge()).query("alpha")

    assert result["ok"] is False
    assert result["fallback"] == "native brain search"
