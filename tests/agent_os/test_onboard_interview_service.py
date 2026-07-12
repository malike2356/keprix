"""Prompt 276 onboard interview service tests."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.agent_os.onboard_interview_service import OnboardInterviewService


def _answer_all(service: OnboardInterviewService, session_id: str) -> None:
    for index in range(1, 8):
        service.answer(session_id, index, f"answer {index}")


def test_onboard_full_flow_writes_context_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    service = OnboardInterviewService()
    session = service.start("demo")

    _answer_all(service, session.session_id)
    completed = service.complete(session.session_id)

    root = tmp_path / ".keprix" / "workspaces" / "demo"
    assert completed.status == "completed"
    assert (root / "context" / "about-business.md").is_file()
    assert (root / "context" / "intake.json").is_file()
    assert (root / "connections.md").is_file()
    assert json.loads((root / "context" / "intake.json").read_text(encoding="utf-8"))["answers"]["q7"] == "answer 7"


def test_onboard_resume_returns_in_progress_session(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    service = OnboardInterviewService()
    session = service.start("demo")
    service.answer(session.session_id, 1, "first")

    resumed = service.start("demo")

    assert resumed.session_id == session.session_id
    assert resumed.current_question == 2
