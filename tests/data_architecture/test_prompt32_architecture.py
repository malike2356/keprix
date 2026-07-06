"""Tests for Prompt 32 data architecture and job queue."""

from __future__ import annotations

import csv
import json
import threading
import uuid
from pathlib import Path

import pytest

from keprix.data_architecture.backup import backup_workspace, restore_workspace
from keprix.data_architecture.control_plane import ControlPlane
from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.jobs.queue import JobQueue
from keprix.research_workspace.obsidian import export_obsidian_vault
from keprix.research_workspace.store import ResearchWorkspaceStore


@pytest.fixture
def workspace_plane(tmp_path: Path) -> WorkspaceDataPlane:
    plane = WorkspaceDataPlane(workspace_id=f"ws-{uuid.uuid4().hex[:6]}")
    plane.root = tmp_path / "workspace"
    plane.db_path = plane.root / "data_plane.sqlite"
    plane.initialize()
    return plane


def test_data_plane_backup_and_restore(workspace_plane: WorkspaceDataPlane):
    with workspace_plane.connect(write=True) as conn:
        conn.execute(
            "INSERT INTO sessions (session_id, workspace_id, agent_id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            ("sess-1", workspace_plane.workspace_id, "agent-1", "user-1", "Test"),
        )
    backup_path = workspace_plane.backup(workspace_plane.root / "backup.sqlite")
    with workspace_plane.connect() as conn:
        conn.execute("DELETE FROM sessions")
    workspace_plane.restore(backup_path)
    with workspace_plane.connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    assert count == 1


def test_control_plane_links_workspace(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "keprix.data_architecture.control_plane._control_plane_path",
        lambda: tmp_path / "registry.json",
    )
    cp = ControlPlane()
    linked = cp.link_data_plane("default", "/tmp/data-plane")
    assert linked["workspace_id"] == "default"
    assert cp.resolve_workspace("default")["data_plane_path"] == "/tmp/data-plane"


def test_job_claim_allows_only_one_worker(workspace_plane: WorkspaceDataPlane):
    queue = JobQueue(workspace_plane.workspace_id)
    queue.plane = workspace_plane
    job = queue.enqueue("data_import", {"dataset": "demo"})
    results: list[dict] = []

    def worker():
        claimed = queue.claim_job(job["job_id"], worker_id=f"worker-{uuid.uuid4().hex[:4]}")
        if claimed:
            results.append(claimed)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(results) == 1


def test_failed_job_moves_to_dead_letter(workspace_plane: WorkspaceDataPlane):
    queue = JobQueue(workspace_plane.workspace_id)
    queue.plane = workspace_plane
    job = queue.enqueue("data_cleaning", {})
    claimed = queue.claim_job(job["job_id"], worker_id="worker-a")
    assert claimed and claimed.get("claim_token")
    for _ in range(3):
        job = queue.fail(job["job_id"], claimed["claim_token"], reason="boom")
        if job and job["status"] == "pending":
            claimed = queue.claim_job(job["job_id"], worker_id="worker-a")
            assert claimed
    assert job is not None
    assert job["status"] == "dead_letter"


def test_dataset_version_records_created(workspace_plane: WorkspaceDataPlane):
    version = workspace_plane.register_dataset_version(
        dataset_id="ds-test",
        name="Survey",
        fmt="csv",
        path="/tmp/survey.csv",
        db_path="/tmp/survey.duckdb",
        engine="duckdb",
        row_count=10,
        lineage={"step": "import"},
    )
    versions = workspace_plane.list_dataset_versions("ds-test")
    assert version["version_id"]
    assert len(versions) == 1
    assert versions[0]["lineage"]["step"] == "import"


def test_obsidian_export_preserves_frontmatter_and_wikilinks(workspace_plane: WorkspaceDataPlane, tmp_path: Path):
    store = ResearchWorkspaceStore(workspace_plane.workspace_id)
    store.plane = workspace_plane
    project = store.create_project(title="Literature review", question="What works?")
    source = store.add_source(project["project_id"], kind="url", ref="https://example.com/paper")
    store.add_claim(project["project_id"], text="Claim one", source_id=source["source_id"], approved=True)
    result = export_obsidian_vault(store, project["project_id"], tmp_path / "vault")
    index = (Path(result["path"]) / "index.md").read_text(encoding="utf-8")
    claim_file = next(Path(result["path"]).glob("claim-*.md"))
    claim_text = claim_file.read_text(encoding="utf-8")
    assert index.startswith("---")
    assert '"research"' in index or "research" in index
    assert "[[index]]" in claim_text
    assert "[[source-" in claim_text


def test_csv_import_creates_version_lineage(tmp_path: Path, workspace_plane: WorkspaceDataPlane):
    csv_path = tmp_path / "sample.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["age", "score"])
        writer.writeheader()
        writer.writerow({"age": "30", "score": "88"})
    version = workspace_plane.register_dataset_version(
        dataset_id="ds-csv",
        name="sample",
        fmt="csv",
        path=str(csv_path),
        db_path=None,
        engine=None,
        row_count=1,
        lineage={"transformations": ["import_csv"]},
    )
    assert version["row_count"] == 1
    stored = workspace_plane.list_dataset_versions("ds-csv")[0]
    assert stored["lineage"]["transformations"] == ["import_csv"]


def test_research_claim_links_to_source_and_citation(workspace_plane: WorkspaceDataPlane):
    store = ResearchWorkspaceStore(workspace_plane.workspace_id)
    store.plane = workspace_plane
    project = store.create_project(title="Citation test", question="Does it link?")
    source = store.add_source(project["project_id"], kind="url", ref="https://example.com/study")
    claim = store.add_claim(
        project["project_id"],
        text="Effect size was significant",
        source_id=source["source_id"],
        approved=True,
    )
    citation = store.add_citation(
        project["project_id"],
        source_id=source["source_id"],
        label="Example 2026",
        metadata={"doi": "10.1000/example"},
    )
    citations = store.list_citations(project["project_id"])
    assert claim["source_id"] == source["source_id"]
    assert any(item["source_id"] == source["source_id"] for item in citations)
    assert citation["citation_id"]


def test_retrieval_graph_edges_link_claim_to_source(workspace_plane: WorkspaceDataPlane, monkeypatch):
    monkeypatch.setattr(
        "keprix.data_architecture.graph_edges.get_workspace_data_plane",
        lambda workspace_id="default": workspace_plane,
    )
    from keprix.data_architecture.graph_edges import add_graph_edge, list_graph_edges

    edge = add_graph_edge(
        workspace_id=workspace_plane.workspace_id,
        source_kind="claim",
        source_id="claim-1",
        target_kind="source",
        target_id="source-1",
        relation="cites",
    )
    rows = list_graph_edges(
        workspace_id=workspace_plane.workspace_id,
        source_kind="claim",
        source_id="claim-1",
    )
    assert edge["edge_id"]
    assert len(rows) == 1
    assert rows[0]["relation"] == "cites"
