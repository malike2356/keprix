from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user
from keprix.brain.coverage import detect_coverage_gaps
from keprix.brain.duplicates import find_duplicate_candidates_fuzzy, fuzzy_similarity
from keprix.brain.graph_types import GraphNode
from keprix.brain.health import BrainHealthService, compute_health_score
from keprix.brain.node_resolvers import NodeResolver
from keprix.data_architecture.graph_edges import add_graph_edge, list_graph_edges, remap_graph_node_edges
from keprix.memory.episodic.store import InMemoryEpisodicStore


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_EMBEDDING_DETERMINISTIC", "1")


def _memory_node(node_id: str, label: str) -> GraphNode:
    return GraphNode(
        id=node_id,
        kind="memory",
        label=label,
        summary=label,
        created_at=datetime.now(timezone.utc),
    )


def test_health_score_formula() -> None:
    score = compute_health_score(
        total_nodes=100,
        orphan_count=10,
        stale_count=10,
        duplicate_group_count=2,
        hub_count=5,
    )
    assert 50 <= score <= 80


def test_duplicate_detection_groups_similar_memories() -> None:
    memories = [
        _memory_node("a", "Client prefers PDF invoices for billing"),
        _memory_node("b", "PDF invoices preferred by client for billing"),
        _memory_node("c", "Completely unrelated scheduling note"),
    ]
    groups = find_duplicate_candidates_fuzzy(memories)
    assert groups
    assert {"a", "b"} <= set(groups[0])
    assert fuzzy_similarity(memories[0].summary, memories[1].summary) >= 0.60


def test_coverage_gap_detection_finds_thin_topics() -> None:
    memories = [
        _memory_node("1", "billing disputes workflow"),
        _memory_node("2", "cancellation policy draft"),
        _memory_node("3", "GDPR requests intake"),
        _memory_node("4", "scheduling reminders for onboarding"),
        _memory_node("5", "billing disputes escalation"),
        _memory_node("6", "scheduling reminders follow up"),
        _memory_node("7", "scheduling reminders weekly"),
        _memory_node("8", "security incident response"),
        _memory_node("9", "security incident triage"),
        _memory_node("10", "security incident playbook"),
    ]
    gaps = detect_coverage_gaps(memories)
    assert len(gaps) >= 2


@pytest.mark.asyncio
async def test_brain_health_service_orphans_stale_and_merge(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = "health-workspace"
    store = InMemoryEpisodicStore()
    orphan_id = await store.save(workspace_id, "Random thought from January")
    connected_id = await store.save(workspace_id, "Client prefers PDF invoices")
    duplicate_id = await store.save(workspace_id, "PDF invoices preferred by client")
    add_graph_edge(
        workspace_id=workspace_id,
        source_kind="memory",
        source_id=connected_id,
        target_kind="session",
        target_id="sess-1",
        relation="derived_from",
    )
    add_graph_edge(
        workspace_id=workspace_id,
        source_kind="memory",
        source_id=duplicate_id,
        target_kind="session",
        target_id="sess-1",
        relation="derived_from",
    )

    service = BrainHealthService(resolver=NodeResolver())
    monkeypatch.setattr(service, "episodic_store", store)

    report = await service.build_report(workspace_id)

    assert report.orphan_count >= 1
    assert any(node.id == orphan_id for node in report.orphan_nodes)
    assert report.hub_nodes
    assert report.health_score >= 0

    deleted = await service.delete_orphans(workspace_id)
    assert deleted >= 1

    remapped = remap_graph_node_edges(
        workspace_id=workspace_id,
        from_kind="memory",
        from_id=duplicate_id,
        to_kind="memory",
        to_id=connected_id,
    )
    assert remapped >= 1
    await store.delete(workspace_id, duplicate_id)
    edges = list_graph_edges(workspace_id=workspace_id, limit=50)
    assert all(edge["source_id"] != duplicate_id and edge["target_id"] != duplicate_id for edge in edges)


def test_brain_health_routes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = "health-routes"
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    store = InMemoryEpisodicStore()

    import asyncio

    orphan_id = asyncio.run(store.save(workspace_id, "Scratch orphan note"))
    assert orphan_id

    app = create_app()
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user", "workspace_id": workspace_id}
    monkeypatch.setattr("keprix.brain.health.create_episodic_store", lambda: store)

    health = client.get(f"/api/brain/health?workspace_id={workspace_id}&refresh=true")
    assert health.status_code == 200
    payload = health.json()
    assert payload["orphan_count"] >= 1
    assert payload["health_label"] in {"Excellent", "Good", "Needs attention", "Poor"}

    denied = client.post(
        f"/api/brain/health/delete-orphans?workspace_id={workspace_id}",
        json={"confirm": False},
    )
    assert denied.status_code == 400

    deleted = client.post(
        f"/api/brain/health/delete-orphans?workspace_id={workspace_id}",
        json={"confirm": True},
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] >= 1

    refreshed = client.get(f"/api/brain/health?workspace_id={workspace_id}&refresh=true")
    assert refreshed.json()["orphan_count"] == 0
