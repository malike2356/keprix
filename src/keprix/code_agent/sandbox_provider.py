"""Sandbox execution provider interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SandboxResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SandboxSession:
    session_id: str
    workspace_id: str
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SandboxProvider(ABC):
    name: str = "base"

    @abstractmethod
    def start(self, workspace_id: str) -> SandboxSession: ...

    @abstractmethod
    def run_code(self, session_id: str, code: str) -> SandboxResult: ...

    @abstractmethod
    def stop(self, session_id: str) -> None: ...

    def create_session_id(self) -> str:
        return str(uuid.uuid4())
