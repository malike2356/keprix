"""Capability graph loader tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from keprix.capability_mesh import CapabilityGraphError, load_graph
from keprix.capability_mesh.graph import default_graph_path, iter_seed_required_ids


def test_default_seed_loads_and_has_required_nodes() -> None:
    graph = load_graph()
    assert graph.version == 1
    for node_id in iter_seed_required_ids():
        assert node_id in graph.nodes
    ch = graph.get_node("companies-house")
    assert ch.status == "wired"
    assert "search:companies_house" in ch.tools
    assert "telegram" in ch.channel_surfaces


def test_neighbors_vical_to_calendar() -> None:
    graph = load_graph()
    outs = graph.neighbors("vical", direction="out")
    targets = {node.id for _, node in outs}
    assert "calendar" in targets
    assert "contacts" in targets
    edge_fields = {edge.via_id_field for edge, _ in outs}
    assert "workspace_event_id" in edge_fields


def test_tools_for_and_channel_ready() -> None:
    graph = load_graph()
    assert graph.tools_for("companies-house")[0].startswith("search:")
    telegram_wired = graph.channel_ready("telegram", require_wired=True)
    assert any(n.id == "companies-house" for n in telegram_wired)
    assert all(n.status == "wired" for n in telegram_wired)


def test_rejects_duplicate_nodes(tmp_path: Path) -> None:
    payload = {
        "version": 1,
        "nodes": [
            {"id": "a", "label": "A", "status": "ui_only"},
            {"id": "a", "label": "A2", "status": "ui_only"},
        ],
        "edges": [],
    }
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(CapabilityGraphError, match="duplicate"):
        load_graph(path)


def test_rejects_dangling_edge(tmp_path: Path) -> None:
    payload = {
        "version": 1,
        "nodes": [{"id": "a", "label": "A", "status": "ui_only"}],
        "edges": [{"from": "a", "to": "missing", "relation": "references"}],
    }
    path = tmp_path / "dangling.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(CapabilityGraphError, match="dangling"):
        load_graph(path)


def test_default_path_points_at_package_yaml() -> None:
    path = default_graph_path()
    assert path.name == "capability_graph.yaml"
    assert path.is_file()
