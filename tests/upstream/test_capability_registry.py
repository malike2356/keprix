"""Tests for capability registry matching."""

from __future__ import annotations

from keprix.upstream.capability_registry import clear_registry_cache, load_capability_map, match_capability
from keprix.upstream.inventory_store import refresh_keprix_features


def test_load_capability_map_has_core_ids():
    clear_registry_cache()
    caps = load_capability_map()
    assert "tools-mcp" in caps
    assert "tui-command-center" in caps


def test_match_capability_alias_boost():
    clear_registry_cache()
    cap_id, score = match_capability("New browser automation MCP tool")
    assert cap_id == "tools-mcp"
    # Soft hint only; auto already_have requires score >= 0.7 in the monitor.
    assert score >= 0.35


def test_match_capability_strong_overlap():
    clear_registry_cache()
    cap_id, score = match_capability(
        "conversation loop agent engine tool calling streaming sessions runtime"
    )
    assert cap_id == "agent-runtime"
    assert score >= 0.5


def test_refresh_keprix_features(tmp_path):
    path = tmp_path / "inv.yaml"
    path.write_text("keprix_features: {}\ntracked_features: {}\n", encoding="utf-8")
    caps = refresh_keprix_features(path)
    assert len(caps) >= 15
    assert "scout-security" in caps
