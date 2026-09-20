"""Recorded-session snapshot tests (prompt 772). Offline; no LLM API keys."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from keprix.trajectory.recorded import (
    FixtureValidationError,
    load_fixture,
    run_recorded_fixture,
    scrub_fixture_dict,
    write_fixture,
)
from keprix.trajectory.recorded.fixture import validate_fixture_dict
from keprix.trajectory.recorded.harness import export_recorded_fixture
from keprix.trajectory.service import reset_trajectory_service_for_tests


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "trajectories"

# Keys that must not be required for these tests.
_LLM_ENV_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "KEPRIX_LLM_API_KEY",
)


@pytest.fixture
def offline_env(monkeypatch: pytest.MonkeyPatch):
    for key in _LLM_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield


@pytest.mark.parametrize(
    "name",
    ["soft-wall-deny", "multi-tool-success", "mutation-propose-stub"],
)
def test_recorded_fixture_replays_offline(name: str, tmp_path: Path, offline_env):
    path = FIXTURES / f"{name}.json"
    assert path.is_file(), f"missing fixture {path}"
    for key in _LLM_ENV_KEYS:
        assert key not in os.environ
    report = run_recorded_fixture(path, sqlite_path=tmp_path / f"{name}.db")
    assert report.fixture_id == name
    assert report.step_count >= 3
    assert report.replay["mode"] == "recorded"
    assert all(step["execute"] is False for step in report.replay["steps"])


def test_soft_wall_deny_asserts_denied(tmp_path: Path, offline_env):
    report = run_recorded_fixture(
        FIXTURES / "soft-wall-deny.json",
        sqlite_path=tmp_path / "sw.db",
    )
    assert report.soft_wall_outcomes == ["denied"]
    assert report.tool_names_in_order == ["terminal"]
    assert report.mutation_stages == []


def test_multi_tool_order(tmp_path: Path, offline_env):
    report = run_recorded_fixture(
        FIXTURES / "multi-tool-success.json",
        sqlite_path=tmp_path / "mt.db",
    )
    assert report.tool_names_in_order == ["read_file", "memory_search"]
    assert report.soft_wall_outcomes == ["allowed", "allowed"]


def test_mutation_stub_propose(tmp_path: Path, offline_env):
    report = run_recorded_fixture(
        FIXTURES / "mutation-propose-stub.json",
        sqlite_path=tmp_path / "mut.db",
    )
    assert report.mutation_stages == ["propose", "approve", "mount"]
    assert report.tool_names_in_order == []


def test_scrubber_redacts_secrets():
    dirty = {
        "schema_version": 1,
        "fixture_id": "dirty",
        "expectations": {"require_recorded_replay": True},
        "events": [
            {
                "seq": 1,
                "event_type": "message",
                "timestamp": "2026-01-01T00:00:00Z",
                "payload": {
                    "api_key": "sk-live-SHOULD_NOT_PERSIST_1234567890",
                    "note": "ok",
                },
                "tool_name": None,
                "soft_wall_outcome": None,
                "error_text": None,
            }
        ],
    }
    clean = scrub_fixture_dict(dirty)
    assert clean["events"][0]["payload"]["api_key"] == "[redacted]"
    assert clean["events"][0]["payload"]["note"] == "ok"


def test_loader_rejects_bad_schema(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema_version": 99, "fixture_id": "x"}), encoding="utf-8")
    with pytest.raises(FixtureValidationError):
        load_fixture(path)


def test_validate_rejects_unsanitized_token_blob():
    data = {
        "schema_version": 1,
        "fixture_id": "leak",
        "expectations": {},
        "events": [
            {
                "seq": 1,
                "event_type": "note",
                "payload": {"text": "token ghp_abcdefghijklmnopqrstuvwx"},
            }
        ],
    }
    # Bypass scrub: validate raw
    with pytest.raises(FixtureValidationError):
        validate_fixture_dict(data)


def test_export_roundtrip(tmp_path: Path, offline_env):
    svc = reset_trajectory_service_for_tests(sqlite_path=tmp_path / "export.db")
    traj = svc.create(workspace_id="fixture", title="export-src")
    tid = traj["trajectory_id"]
    svc.append(tid, "message", {"role": "user", "text": "hi"})
    svc.record_soft_wall(tid, outcome="denied", tool_name="terminal")
    svc.append(tid, "message", {"role": "assistant", "status": "blocked", "text": "no"})
    out = tmp_path / "exported.json"
    export_recorded_fixture(
        svc,
        tid,
        fixture_id="export-roundtrip",
        path=out,
        expectations={
            "require_recorded_replay": True,
            "forbid_live_execute": True,
            "soft_wall_outcomes": ["denied"],
            "final_message_shape": {"role": "assistant", "status": "blocked"},
        },
        title="export roundtrip",
    )
    report = run_recorded_fixture(out, sqlite_path=tmp_path / "replay.db")
    assert report.soft_wall_outcomes == ["denied"]


def test_write_fixture_is_scrubbed(tmp_path: Path):
    path = tmp_path / "out.json"
    write_fixture(
        path,
        {
            "schema_version": 1,
            "fixture_id": "write-scrub",
            "expectations": {"require_recorded_replay": True},
            "events": [
                {
                    "seq": 1,
                    "event_type": "message",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "payload": {"password": "hunter2", "role": "user", "text": "x"},
                    "tool_name": None,
                    "soft_wall_outcome": None,
                    "error_text": None,
                }
            ],
        },
    )
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["events"][0]["payload"]["password"] == "[redacted]"
