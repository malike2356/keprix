"""Optional E2B sandbox provider."""

from __future__ import annotations

import os

from keprix.code_agent.docker_provider import DockerSandboxProvider
from keprix.code_agent.sandbox_provider import SandboxProvider, SandboxSession, SandboxResult


class E2BSandboxProvider(SandboxProvider):
    name = "e2b"

    def __init__(self) -> None:
        self._api_key = os.environ.get("KEPRIX_E2B_API_KEY", "").strip()
        self._fallback = DockerSandboxProvider()
        self._sessions: dict[str, SandboxSession] = {}

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def start(self, workspace_id: str) -> SandboxSession:
        session = SandboxSession(
            session_id=self.create_session_id(),
            workspace_id=workspace_id,
            provider=self.name if self.configured else "docker-fallback",
        )
        self._sessions[session.session_id] = session
        return session

    def run_code(self, session_id: str, code: str) -> SandboxResult:
        session = self._sessions.get(session_id)
        workspace_id = session.workspace_id if session else "default"
        fallback_session = self._fallback.start(workspace_id)
        try:
            return self._fallback.run_code(fallback_session.session_id, code)
        finally:
            self._fallback.stop(fallback_session.session_id)

    def stop(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
