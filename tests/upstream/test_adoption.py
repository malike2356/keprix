"""Tests for upstream CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from keprix.keprix_cli import upstream_commands
from keprix.upstream.hermes_monitor import AdoptionStatus, FeatureCategory, UpstreamFeature


@pytest.fixture
def inventory_path(tmp_path: Path) -> Path:
    path = tmp_path / "inventory.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "processed_versions": [],
                "keprix_features": {},
                "tracked_features": {
                    "hermes-0.18.0-abc": UpstreamFeature(
                        feature_id="hermes-0.18.0-abc",
                        name="Browser tool",
                        description="New browser automation MCP tool",
                        category=FeatureCategory.TOOL,
                        version_introduced="0.18.0",
                        release_date="2026-07-09T12:00:00Z",
                        release_url="https://example.test",
                        adoption_status=AdoptionStatus.UNEVALUATED,
                        suggested_status=AdoptionStatus.ADOPT_WITH_HARDENING,
                    ).to_dict()
                },
                "next_prompt_number": 500,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_cmd_list_json(inventory_path: Path, capsys):
    args = argparse.Namespace(
        upstream_command="list",
        inventory=str(inventory_path),
        category=None,
        status=None,
        pending=False,
        json=True,
    )
    assert upstream_commands.cmd_upstream(args) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert payload[0]["feature_id"] == "hermes-0.18.0-abc"


def test_cmd_review_and_decide(inventory_path: Path, capsys):
    args = argparse.Namespace(
        upstream_command="review",
        inventory=str(inventory_path),
        json=False,
    )
    assert upstream_commands.cmd_upstream(args) == 0
    assert "Pending review" in capsys.readouterr().out

    decide = argparse.Namespace(
        upstream_command="decide",
        inventory=str(inventory_path),
        feature_id="hermes-0.18.0-abc",
        status="adopt_with_hardening",
        notes="ship it",
        by="tester",
        equivalent=None,
    )
    assert upstream_commands.cmd_upstream(decide) == 0
    assert "adopt_with_hardening" in capsys.readouterr().out


def test_cmd_adopt_requires_decision(inventory_path: Path, tmp_path: Path, capsys):
    args = argparse.Namespace(
        upstream_command="adopt",
        inventory=str(inventory_path),
        feature_id="hermes-0.18.0-abc",
        prompts_dir=str(tmp_path / "prompts"),
        work_packages_dir=str(tmp_path / "work"),
    )
    assert upstream_commands.cmd_upstream(args) == 1
    assert "pending review" in capsys.readouterr().out.lower()

    decide = argparse.Namespace(
        upstream_command="decide",
        inventory=str(inventory_path),
        feature_id="hermes-0.18.0-abc",
        status="adopt_with_hardening",
        notes="",
        by="tester",
        equivalent=None,
    )
    assert upstream_commands.cmd_upstream(decide) == 0
    assert upstream_commands.cmd_upstream(args) == 0
    out = capsys.readouterr().out
    assert "Generated adoption prompt" in out
    files = list((tmp_path / "prompts").glob("500-adopt-hermes-*.md"))
    assert files
    assert list((tmp_path / "work").glob("*.yaml"))


def test_cmd_check_no_features(inventory_path: Path, capsys):
    args = argparse.Namespace(
        upstream_command="check",
        inventory=str(inventory_path),
        json=False,
        no_enrichment=True,
    )
    with patch("keprix.keprix_cli.upstream_commands.asyncio.run", return_value=[]):
        assert upstream_commands.cmd_upstream(args) == 0
    assert "current" in capsys.readouterr().out.lower()


def test_cmd_complete(inventory_path: Path, capsys):
    decide = argparse.Namespace(
        upstream_command="decide",
        inventory=str(inventory_path),
        feature_id="hermes-0.18.0-abc",
        status="adopt_with_hardening",
        notes="",
        by="tester",
        equivalent=None,
    )
    assert upstream_commands.cmd_upstream(decide) == 0
    complete = argparse.Namespace(
        upstream_command="complete",
        inventory=str(inventory_path),
        feature_id="hermes-0.18.0-abc",
        equivalent="tools-mcp",
        notes="done",
        by="tester",
    )
    assert upstream_commands.cmd_upstream(complete) == 0
    assert "already_have" in capsys.readouterr().out
