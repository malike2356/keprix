"""DoD and audit tests (soft gate)."""

from __future__ import annotations

from pathlib import Path

import yaml

from keprix.capability_mesh.audit import render_markdown, run_audit
from keprix.capability_mesh.dod import FEATURE_DOD_CHECKLIST, MESH_PROMPT_TEMPLATE, assert_dod, check_wired_telegram_nodes
from keprix.capability_mesh.graph import load_graph


def test_seed_dod_passes_for_companies_house() -> None:
    result = assert_dod()
    assert result["ok"] is True
    assert result["violation_count"] == 0


def test_dod_fails_when_wired_telegram_missing_toolset_membership(tmp_path: Path) -> None:
    payload = {
        "version": 1,
        "nodes": [
            {
                "id": "fake",
                "label": "Fake",
                "status": "wired",
                "channel_surfaces": ["telegram"],
                "tools": ["definitely_not_a_real_core_tool_xyz"],
            }
        ],
        "edges": [],
    }
    path = tmp_path / "g.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    graph = load_graph(path)
    violations = check_wired_telegram_nodes(graph, platform_tools={"web_search"})
    assert violations
    assert violations[0].code == "tool_not_in_telegram_toolset"


def test_audit_runs_and_tracks_seed_nodes() -> None:
    report = run_audit()
    assert "vical" in report["seed_nodes"]
    assert "companies-house" in report["seed_nodes"]
    assert report["dod"]["ok"] is True
    nav_ids = {row["nav_id"] for row in report["rows"]}
    assert "calendar" in nav_ids
    assert "vical" in nav_ids
    md = render_markdown(report)
    assert "Capability mesh gap report" in md
    assert "Regenerate" in md


def test_dod_checklist_documented() -> None:
    assert len(FEATURE_DOD_CHECKLIST) >= 5
    assert "Agent tool" in MESH_PROMPT_TEMPLATE or "Agent tools" in MESH_PROMPT_TEMPLATE
