"""Tests for sandbox providers."""

from __future__ import annotations

from keprix.code_agent.docker_provider import DockerSandboxProvider
from keprix.code_agent.e2b_provider import E2BSandboxProvider
from keprix.code_agent.modal_provider import ModalSandboxProvider
from keprix.code_agent.sandbox_provider import SandboxResult


def test_docker_provider_runs_simple_code() -> None:
    provider = DockerSandboxProvider()
    session = provider.start("workspace-1")
    try:
        result = provider.run_code(session.session_id, "result = 2 + 2\n")
        assert isinstance(result, SandboxResult)
        assert result.ok
    finally:
        provider.stop(session.session_id)


def test_e2b_provider_falls_back_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("KEPRIX_E2B_API_KEY", raising=False)
    provider = E2BSandboxProvider()
    assert not provider.configured
    session = provider.start("workspace-2")
    try:
        result = provider.run_code(session.session_id, "result = 3 + 3\n")
        assert result.ok
    finally:
        provider.stop(session.session_id)


def test_modal_provider_reports_configured_with_token(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_MODAL_TOKEN", "test-token")
    provider = ModalSandboxProvider()
    assert provider.configured
