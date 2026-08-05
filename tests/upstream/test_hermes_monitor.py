"""Tests for Hermes upstream monitor."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from keprix.upstream.hermes_adoption import AdoptionPromptGenerator
from keprix.upstream.hermes_monitor import (
    AdoptionStatus,
    FeatureCategory,
    HermesMonitor,
    UpstreamFeature,
)
from keprix.upstream.work_package import build_work_package


SAMPLE_RELEASE = {
    "tag_name": "v0.18.0",
    "published_at": "2026-07-09T12:00:00Z",
    "html_url": "https://github.com/NousResearch/hermes-agent/releases/tag/v0.18.0",
    "body": (
        "## Added\n"
        "- New browser automation MCP tool for headless browsing\n"
        "- Faster prompt cache for repeated tool calls\n"
        "## Platform\n"
        "- Experimental Android desktop shell\n"
    ),
}


@pytest.fixture
def inventory_path(tmp_path: Path) -> Path:
    path = tmp_path / "hermes_inventory.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "processed_versions": ["0.17.0"],
                "keprix_features": {
                    "prompt-82": "Operations; prompt cache, spend tracker, format translator"
                },
                "tracked_features": {},
                "next_prompt_number": 400,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_categorise_tool_and_platform():
    monitor = HermesMonitor(inventory_path=Path("/tmp/missing-keprix-upstream-test.yaml"))
    assert monitor._categorise("New browser automation MCP tool", "added") == FeatureCategory.TOOL
    assert monitor._categorise("Android desktop shell", "platform") == FeatureCategory.PLATFORM


def test_evaluate_adoption_marks_platform_skip(inventory_path: Path):
    monitor = HermesMonitor(inventory_path=inventory_path)
    feature = UpstreamFeature(
        feature_id="hermes-0.18.0-test",
        name="Android desktop shell",
        description="Experimental Android desktop shell",
        category=FeatureCategory.PLATFORM,
        version_introduced="0.18.0",
        release_date="2026-07-09T12:00:00Z",
        release_url="https://example.test/release",
    )
    assert monitor._evaluate_adoption(feature) == AdoptionStatus.SKIP


def test_evaluate_adoption_detects_existing_feature(inventory_path: Path):
    monitor = HermesMonitor(inventory_path=inventory_path)
    feature = UpstreamFeature(
        feature_id="hermes-0.18.0-cache",
        name="Prompt cache improvements",
        description="Prompt cache spend tracker format translator improvements",
        category=FeatureCategory.PERFORMANCE,
        version_introduced="0.18.0",
        release_date="2026-07-09T12:00:00Z",
        release_url="https://example.test/release",
    )
    status = monitor._evaluate_adoption(feature)
    assert status == AdoptionStatus.ALREADY_HAVE
    assert feature.keprix_equivalent == "prompt-82"


@pytest.mark.asyncio
async def test_check_parses_new_release(inventory_path: Path):
    monitor = HermesMonitor(inventory_path=inventory_path)

    async def fake_fetch_releases():
        return [SAMPLE_RELEASE]

    async def fake_fetch_pypi():
        return None

    async def fake_changelog():
        return ""

    async def fake_compare(_base, _head):
        return "compare 0.17.0...0.18.0: 1 commits, 2 files"

    with patch.object(monitor, "_fetch_releases", fake_fetch_releases), patch.object(
        monitor, "_fetch_pypi_version", fake_fetch_pypi
    ), patch.object(monitor, "_fetch_changelog", fake_changelog), patch.object(
        monitor, "_fetch_compare_summary", fake_compare
    ), patch.object(monitor, "_emit_release_signal"):
        features = await monitor.check(emit_scout=False, fetch_enrichment=True)

    assert len(features) == 3
    assert any(feature.category == FeatureCategory.TOOL for feature in features)
    # Human gate: non-matched features stay unevaluated with suggested status.
    tool = next(f for f in features if f.category == FeatureCategory.TOOL)
    assert tool.adoption_status == AdoptionStatus.UNEVALUATED
    assert tool.suggested_status == AdoptionStatus.ADOPT_WITH_HARDENING
    assert any(feature.adoption_status == AdoptionStatus.UNEVALUATED for feature in features)
    assert any(
        feature.suggested_status == AdoptionStatus.SKIP for feature in features
    )
    saved = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))
    assert "0.18.0" in saved["processed_versions"]
    assert len(saved["tracked_features"]) == 3


def test_decide_and_adopt_requires_approval(inventory_path: Path, tmp_path: Path):
    monitor = HermesMonitor(inventory_path=inventory_path)
    feature = UpstreamFeature(
        feature_id="hermes-0.18.0-browser",
        name="New browser automation MCP tool",
        description="New browser automation MCP tool for headless browsing",
        category=FeatureCategory.TOOL,
        version_introduced="0.18.0",
        release_date="2026-07-09T12:00:00Z",
        release_url="https://example.test/release",
        adoption_status=AdoptionStatus.UNEVALUATED,
        suggested_status=AdoptionStatus.ADOPT_WITH_HARDENING,
        security_implications=["Emit Scout signals for tool invocation."],
    )
    monitor.inventory["tracked_features"] = {feature.feature_id: feature.to_dict()}
    monitor._save_inventory()

    generator = AdoptionPromptGenerator(
        monitor,
        prompts_dir=tmp_path / "prompts",
        work_packages_dir=tmp_path / "work",
    )
    with pytest.raises(PermissionError):
        generator.generate(feature.feature_id)

    monitor.decide(feature.feature_id, "adopt_with_hardening", notes="ok")
    output = generator.generate(feature.feature_id)
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "Adopt Hermes Feature" in text
    assert "browser automation" in text
    saved = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))
    assert saved["next_prompt_number"] == 401
    updated = UpstreamFeature.from_dict(saved["tracked_features"][feature.feature_id])
    assert updated.work_package_path
    assert Path(updated.work_package_path).exists()


def test_mark_complete_updates_registry(inventory_path: Path):
    monitor = HermesMonitor(inventory_path=inventory_path)
    feature = UpstreamFeature(
        feature_id="hermes-0.18.0-browser",
        name="Browser tool",
        description="browser MCP tool",
        category=FeatureCategory.TOOL,
        version_introduced="0.18.0",
        release_date="2026-07-09T12:00:00Z",
        release_url="https://example.test",
        adoption_status=AdoptionStatus.ADOPT_WITH_HARDENING,
        decided_at="2026-07-09T12:00:00Z",
        decided_by="operator",
    )
    monitor.inventory["tracked_features"] = {feature.feature_id: feature.to_dict()}
    monitor._save_inventory()
    done = monitor.mark_complete(feature.feature_id, keprix_equivalent="tools-mcp")
    assert done.adoption_status == AdoptionStatus.ALREADY_HAVE
    assert "tools-mcp" in monitor.inventory["keprix_features"]


def test_work_package_requires_approved_status(tmp_path: Path):
    feature = UpstreamFeature(
        feature_id="f1",
        name="Tool",
        description="browser MCP tool",
        category=FeatureCategory.TOOL,
        version_introduced="0.18.0",
        release_date="2026-07-09T12:00:00Z",
        release_url="https://example.test",
        adoption_status=AdoptionStatus.UNEVALUATED,
    )
    with pytest.raises(ValueError):
        build_work_package(feature, output_dir=tmp_path)


def test_feature_diff_report(inventory_path: Path):
    monitor = HermesMonitor(inventory_path=inventory_path)
    monitor.inventory["tracked_features"] = {
        "f1": UpstreamFeature(
            feature_id="f1",
            name="Tool",
            description="browser MCP tool",
            category=FeatureCategory.TOOL,
            version_introduced="0.18.0",
            release_date="2026-07-09T12:00:00Z",
            release_url="https://example.test",
            adoption_status=AdoptionStatus.ADOPT_WITH_HARDENING,
            decided_at="2026-07-09T12:00:00Z",
            decided_by="operator",
        ).to_dict()
    }
    diff = monitor.feature_diff()
    assert diff["tracked_hermes_features"] == 1
    assert diff["adoptable_features"] == 1
    report = monitor.report()
    assert report["tracked_features"] == 1
    assert "by_category" in report
