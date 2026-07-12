"""Agent OS onboard interview flow."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.agent_os.onboard_store import OnboardSession, OnboardStore
from keprix.agent_os.onboard_templates import QUESTIONS, question_payload, write_onboard_files
from keprix.workspace.template_presets import workspace_root


class OnboardInterviewService:
    def __init__(self, store: OnboardStore | None = None) -> None:
        self.store = store or OnboardStore()

    def start(self, workspace_id: str, *, resume: bool = True) -> OnboardSession:
        if resume:
            existing = self.store.latest_for_workspace(workspace_id)
            if existing and existing.status == "in_progress":
                return existing
        return self.store.create(workspace_id)

    def answer(self, session_id: str, question: int, text: str) -> OnboardSession:
        session = self._require(session_id)
        if session.status == "completed":
            return session
        if question < 1 or question > len(QUESTIONS):
            raise ValueError("question must be between 1 and 7")
        if question != session.current_question:
            raise ValueError(f"expected answer for question {session.current_question}")
        session.answers[f"q{question}"] = text.strip()
        session.current_question = min(len(QUESTIONS) + 1, question + 1)
        return self.store.save(session)

    def complete(self, session_id: str, *, workspace_path: str | None = None) -> OnboardSession:
        session = self._require(session_id)
        missing = [f"q{index}" for index in range(1, len(QUESTIONS) + 1) if not session.answers.get(f"q{index}")]
        if missing:
            raise ValueError(f"missing answers: {', '.join(missing)}")
        root = Path(workspace_path).expanduser().resolve() if workspace_path else workspace_root(session.workspace_id)
        root.mkdir(parents=True, exist_ok=True)
        session.output_paths = write_onboard_files(root, session.answers)
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc).isoformat()
        session.current_question = len(QUESTIONS) + 1
        return self.store.save(session)

    def get(self, session_id: str) -> OnboardSession | None:
        return self.store.get(session_id)

    def questions(self) -> list[dict[str, str]]:
        return question_payload()

    def _require(self, session_id: str) -> OnboardSession:
        session = self.store.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session
