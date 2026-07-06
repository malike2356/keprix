"""Shared fixtures for Opportunity Engine tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.registry import reset_opportunity_registry
from keprix.security.rate_limiter import reset_rate_limits

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "opportunity"


@pytest.fixture
def opp_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(data_dir))
    reset_rate_limits()
    reset_opportunity_registry(base_dir=data_dir / "workspace" / "opportunities")
    return {"data_dir": data_dir, "root": data_dir / "workspace" / "opportunities"}


def load_opportunity_fixture(name: str) -> dict[str, Any]:
    path = FIXTURES_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def opportunity_request_from_fixture(payload: dict[str, Any]) -> OpportunityRequest:
    return OpportunityRequest(
        title=payload["title"],
        niche=payload.get("niche"),
        market=payload.get("market"),
        goal=payload.get("goal"),
        geography=payload.get("geography"),
        buyer_type=payload.get("buyer_type"),
        research_depth=payload.get("research_depth", "standard"),
        source="fixture",
    )
