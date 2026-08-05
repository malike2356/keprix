"""Cordon compatibility tests."""

from __future__ import annotations

import asyncio
import socket
from pathlib import Path

from keprix.config.health_monitor import ConfigHealthMonitor
from keprix.proxy.cordon_bridge import CordonHealthCheck, PROVIDER_ROUTES, provider_route_table, proxy_env_contract, render_cordon_template


def test_provider_routes_cover_expected_llm_hosts() -> None:
    hosts = {route.host for route in PROVIDER_ROUTES}

    assert len(PROVIDER_ROUTES) == 10
    assert {
        "api.anthropic.com",
        "api.openai.com",
        "generativelanguage.googleapis.com",
        "api.deepseek.com",
        "api.groq.com",
        "openrouter.ai",
        "api.mistral.ai",
        "api.together.xyz",
        "api.fireworks.ai",
        "api.x.ai",
    } <= hosts
    assert all(row["secret_ref"].endswith("-api-key") for row in provider_route_table())


def test_cordon_template_matches_skill_template() -> None:
    generated = render_cordon_template()
    skill_template = Path("src/keprix/optional-skills/devops/cordon/templates/cordon.toml.template").read_text(encoding="utf-8")

    for route in PROVIDER_ROUTES:
        assert route.host in generated
        assert route.secret_ref in skill_template
    assert generated.count("[[routes]]") == 10
    assert skill_template.count("[[routes]]") == 10


def test_proxy_env_contract_uses_dummy_keys() -> None:
    env = proxy_env_contract("http://127.0.0.1:6790")

    assert env["HTTPS_PROXY"] == "http://127.0.0.1:6790"
    assert env["ANTHROPIC_API_KEY"] == "dummy-replaced-by-proxy"
    assert env["OPENAI_API_KEY"] == "dummy-replaced-by-proxy"


def test_cordon_health_check_reports_listening_proxy(monkeypatch) -> None:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    monkeypatch.setenv("HTTPS_PROXY", f"http://127.0.0.1:{port}")
    try:
        health = asyncio.run(CordonHealthCheck().check())
    finally:
        sock.close()

    assert health.name == "credential-proxy"
    assert health.status == "healthy"


def test_health_monitor_includes_credential_proxy(monkeypatch) -> None:
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monitor = ConfigHealthMonitor()

    result = asyncio.run(monitor._check_credential_proxy())

    assert result[0].name == "credential-proxy"
    assert result[0].status in {"healthy", "degraded", "down"}
