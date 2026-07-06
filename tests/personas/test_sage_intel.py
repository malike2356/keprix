"""Tests for SAGE intel module."""

from __future__ import annotations

import pytest

from keprix.personas.sage.intel import MonitoredSource, SageIntel
from keprix.personas.sage.researcher import Confidence


@pytest.fixture
def intel() -> SageIntel:
    return SageIntel(workspace_id="ws-sage")


def test_configure_and_list_sources(intel: SageIntel) -> None:
    source = MonitoredSource(id="s1", name="Competitor Blog", url="https://competitor.example.com", source_type="site")
    intel.configure_sources([source])
    assert len(intel.list_sources()) == 1


def test_analyze_signals_detects_growth(intel: SageIntel) -> None:
    snippets = [
        {"title": "Market growth surge", "url": "https://news.example.com/1", "snippet": "Adoption and growth increased."},
        {"title": "Industry expansion", "url": "https://www.edu.ac.uk/2", "snippet": "Expanding market footprint."},
    ]
    report = intel.analyze_signals(topic="AI tools", snippets=snippets, competitors=["Acme Corp"])
    assert report.signals
    assert any(signal.signal_type == "growth" for signal in report.signals)


def test_analyze_signals_high_confidence_for_edu(intel: SageIntel) -> None:
    snippets = [{"title": "Study", "url": "https://www.edu.ac.uk/paper", "snippet": "Research on trends."}]
    report = intel.analyze_signals(topic="trends", snippets=snippets)
    assert report.signals[0].confidence == Confidence.HIGH


@pytest.mark.asyncio
async def test_monitoring_cycle_returns_report(intel: SageIntel) -> None:
    report = await intel.run_monitoring_cycle(topic="cloud computing", competitors=["AWS", "Azure"])
    assert report.report_id
    assert len(report.signals) >= 1


def test_schedule_monitoring_creates_cron_job(intel: SageIntel, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_create_job(**kwargs):
        captured.update(kwargs)
        return {"id": "intel-job-1", "enabled": True}

    monkeypatch.setattr("keprix.cron.jobs.create_job", fake_create_job)
    result = intel.schedule_monitoring(topic="AI agents", schedule="0 7 * * *", competitors=["OpenAI"])
    assert result["job_id"] == "intel-job-1"
    assert "AI agents" in captured.get("prompt", "")

