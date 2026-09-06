"""Tests for cost-based model routing (prompt 10). Default off, byte-identical."""

from __future__ import annotations

import pytest

from keprix.providers import routing as rt
from keprix.providers.routing import RoutingConfig, route_model


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    rt._ROUTING_CONFIGS.clear()
    rt._budgets.clear()
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    yield


def test_disabled_returns_cheap():
    d = route_model("ws1", "cheap", "prov1", turn_text="refactor the whole auth layer")
    assert d.model == "cheap"
    assert d.escalated is False
    assert d.reason == "routing_disabled"


def test_simple_turn_stays_cheap_when_enabled():
    cfg = RoutingConfig(
        enabled=True,
        cheap_model="cheap",
        strong_model="strong",
        strong_provider="prov2",
        complexity_threshold=60,
        hourly_budget_credits=100,
    )
    d = route_model("ws1", "cheap", "prov1", turn_text="hi, thanks", config=cfg)
    assert d.model == "cheap"
    assert d.escalated is False
    assert d.reason == "below_threshold"


def test_hard_turn_escalates():
    cfg = RoutingConfig(
        enabled=True,
        cheap_model="cheap",
        strong_model="strong",
        strong_provider="prov2",
        complexity_threshold=60,
        hourly_budget_credits=1000,
    )
    # refactor + debug + security + architecture + implement = 60+ (5 hard signals)
    d = route_model(
        "ws1",
        "cheap",
        "prov1",
        turn_text="refactor and debug the security architecture and implement the migration",
        config=cfg,
    )
    assert d.model == "strong"
    assert d.escalated is True
    assert d.reason.startswith("escalated_score_")


def test_budget_exhausted_falls_back_to_cheap():
    cfg = RoutingConfig(
        enabled=True,
        cheap_model="cheap",
        strong_model="strong",
        strong_provider="prov2",
        complexity_threshold=10,
        hourly_budget_credits=1,
    )
    # first hard turn spends the (tiny) budget
    d1 = route_model("ws1", "cheap", "prov1", turn_text="implement a complex feature", config=cfg)
    assert d1.escalated is True
    # second hard turn: budget exhausted -> cheap
    d2 = route_model(
        "ws1", "cheap", "prov1", turn_text="implement another complex feature", config=cfg
    )
    assert d2.model == "cheap"
    assert d2.reason == "budget_exhausted"


def test_complexity_score_bounds():
    assert 0 <= rt.complexity_score("hi there") <= 100
    assert rt.complexity_score("refactor debug security implement") > rt.complexity_score(
        "hi thanks ok"
    )


def test_audit_written(tmp_path):
    cfg = RoutingConfig(
        enabled=True,
        cheap_model="cheap",
        strong_model="strong",
        strong_provider="p2",
        complexity_threshold=10,
        hourly_budget_credits=100,
    )
    route_model("ws1", "cheap", "p1", turn_text="refactor", config=cfg)
    audit = tmp_path / "routing" / "routing-audit.jsonl"
    assert audit.is_file()
    lines = audit.read_text().strip().splitlines()
    assert len(lines) >= 1
    assert '"escalated"' in lines[0]
