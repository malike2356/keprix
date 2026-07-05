"""
Tests for LongHorizonSession (OpenHands-style multi-step coding sessions, Prompt 64 gap).

Covers: step accumulation, file tracking, transcript, checkpoint, resume.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_session(tmp_path: Path, workspace_id: str = "test-ws"):
    from keprix.code_agent.session_manager import LongHorizonSession

    return LongHorizonSession(workspace_id=workspace_id, checkpoint_dir=tmp_path)


# ---------------------------------------------------------------------------
# Session creation
# ---------------------------------------------------------------------------


class TestSessionCreation:
    def test_session_has_unique_id(self, tmp_path):
        a = make_session(tmp_path, "ws-a")
        b = make_session(tmp_path, "ws-b")
        assert a.session_id != b.session_id

    def test_session_id_can_be_provided(self, tmp_path):
        from keprix.code_agent.session_manager import LongHorizonSession

        s = LongHorizonSession(session_id="fixed-id-123", workspace_id="w", checkpoint_dir=tmp_path)
        assert s.session_id == "fixed-id-123"

    def test_step_count_starts_at_zero(self, tmp_path):
        s = make_session(tmp_path)
        assert s.step_count() == 0

    def test_files_touched_starts_empty(self, tmp_path):
        s = make_session(tmp_path)
        assert s.files_touched() == []


# ---------------------------------------------------------------------------
# Running steps
# ---------------------------------------------------------------------------


class TestRunSteps:
    def test_step_count_increments(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("print hello world")
        assert s.step_count() == 1
        s.run_step("compute 1+1")
        assert s.step_count() == 2

    def test_step_has_step_number(self, tmp_path):
        s = make_session(tmp_path)
        step1 = s.run_step("first task")
        step2 = s.run_step("second task")
        assert step1.step_number == 1
        assert step2.step_number == 2

    def test_step_has_unique_id(self, tmp_path):
        s = make_session(tmp_path)
        step1 = s.run_step("task a")
        step2 = s.run_step("task b")
        assert step1.step_id != step2.step_id

    def test_step_captures_task_name(self, tmp_path):
        s = make_session(tmp_path)
        step = s.run_step("write the data pipeline")
        assert step.task == "write the data pipeline"

    def test_step_has_timestamp(self, tmp_path):
        s = make_session(tmp_path)
        step = s.run_step("any task")
        assert len(step.timestamp) > 0

    def test_step_files_tracked(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("edit config", files=["src/config.py"])
        assert "src/config.py" in s.files_touched()

    def test_files_accumulated_across_steps(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("edit a", files=["src/a.py"])
        s.run_step("edit b", files=["src/b.py"])
        touched = s.files_touched()
        assert "src/a.py" in touched
        assert "src/b.py" in touched

    def test_duplicate_files_not_double_counted(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("edit a", files=["src/shared.py"])
        s.run_step("edit a again", files=["src/shared.py"])
        assert s.files_touched().count("src/shared.py") == 1

    def test_step_to_dict_has_required_keys(self, tmp_path):
        s = make_session(tmp_path)
        step = s.run_step("sample task")
        d = step.to_dict()
        for key in ("step_id", "step_number", "task", "code", "ok", "stdout", "stderr", "errors", "timestamp"):
            assert key in d, f"Missing key: {key}"

    def test_last_step_returns_most_recent(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("first")
        step = s.run_step("second")
        assert s.last_step() is step

    def test_last_step_returns_none_on_empty_session(self, tmp_path):
        s = make_session(tmp_path)
        assert s.last_step() is None


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------


class TestTranscript:
    def test_transcript_includes_session_id(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("task one")
        t = s.transcript()
        assert s.session_id in t

    def test_transcript_includes_workspace_id(self, tmp_path):
        s = make_session(tmp_path, workspace_id="my-workspace")
        t = s.transcript()
        assert "my-workspace" in t

    def test_transcript_includes_step_tasks(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("implement the parser module")
        t = s.transcript()
        assert "implement the parser module" in t

    def test_transcript_labels_step_number(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("step one")
        s.run_step("step two")
        t = s.transcript()
        assert "Step 1" in t
        assert "Step 2" in t

    def test_empty_session_transcript_still_renders(self, tmp_path):
        s = make_session(tmp_path)
        t = s.transcript()
        assert s.session_id in t


# ---------------------------------------------------------------------------
# Checkpoint and resume
# ---------------------------------------------------------------------------


class TestCheckpointResume:
    def test_checkpoint_creates_json_file(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("task one")
        path = s.checkpoint()
        assert path.exists()
        assert path.suffix == ".json"

    def test_checkpoint_file_named_by_session_id(self, tmp_path):
        s = make_session(tmp_path)
        path = s.checkpoint()
        assert s.session_id in path.name

    def test_checkpoint_file_is_valid_json(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("write hello world")
        path = s.checkpoint()
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert "session_id" in raw
        assert "steps" in raw

    def test_checkpoint_persists_step_count(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("step a")
        s.run_step("step b")
        path = s.checkpoint()
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert len(raw["steps"]) == 2

    def test_checkpoint_persists_files_touched(self, tmp_path):
        s = make_session(tmp_path)
        s.run_step("edit module", files=["src/module.py"])
        path = s.checkpoint()
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert "src/module.py" in raw["files_touched"]

    def test_resume_restores_session_id(self, tmp_path):
        from keprix.code_agent.session_manager import LongHorizonSession

        s = make_session(tmp_path)
        original_id = s.session_id
        path = s.checkpoint()
        resumed = LongHorizonSession.resume(path)
        assert resumed.session_id == original_id

    def test_resume_restores_step_count(self, tmp_path):
        from keprix.code_agent.session_manager import LongHorizonSession

        s = make_session(tmp_path)
        s.run_step("task one")
        s.run_step("task two")
        path = s.checkpoint()
        resumed = LongHorizonSession.resume(path)
        assert resumed.step_count() == 2

    def test_resume_restores_files_touched(self, tmp_path):
        from keprix.code_agent.session_manager import LongHorizonSession

        s = make_session(tmp_path)
        s.run_step("edit", files=["src/app.py", "src/models.py"])
        path = s.checkpoint()
        resumed = LongHorizonSession.resume(path)
        touched = resumed.files_touched()
        assert "src/app.py" in touched
        assert "src/models.py" in touched

    def test_resume_continues_step_numbering(self, tmp_path):
        from keprix.code_agent.session_manager import LongHorizonSession

        s = make_session(tmp_path)
        s.run_step("first task")
        path = s.checkpoint()
        resumed = LongHorizonSession.resume(path)
        next_step = resumed.run_step("continued task")
        assert next_step.step_number == 2

    def test_resume_missing_file_raises(self, tmp_path):
        from keprix.code_agent.session_manager import LongHorizonSession

        with pytest.raises(FileNotFoundError):
            LongHorizonSession.resume(tmp_path / "nonexistent.json")

    def test_checkpoint_returns_path_object(self, tmp_path):
        s = make_session(tmp_path)
        path = s.checkpoint()
        assert isinstance(path, Path)


# ---------------------------------------------------------------------------
# SessionStep round-trip serialization
# ---------------------------------------------------------------------------


class TestSessionStepSerialization:
    def test_from_dict_round_trip(self):
        from keprix.code_agent.session_manager import SessionStep

        step = SessionStep(
            step_id="s1",
            step_number=1,
            task="write tests",
            code="print('hello')",
            ok=True,
            stdout="hello\n",
            stderr="",
            result={"output": "hello"},
            errors=[],
            files_edited=["tests/test_foo.py"],
            needs_approval=False,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        d = step.to_dict()
        restored = SessionStep.from_dict(d)
        assert restored.step_id == step.step_id
        assert restored.task == step.task
        assert restored.files_edited == step.files_edited
