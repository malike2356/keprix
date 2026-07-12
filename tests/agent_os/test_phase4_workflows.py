"""Prompt 270 Phase 4 advanced workflows + milestones."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.agent_apps.catalog import list_catalog_templates, template_dir
from keprix.agent_apps.local_runner import run_local
from keprix.agent_os.milestones import build_milestones
from keprix.agent_os.onboarding_progress import OnboardingProgressStore
from keprix.agent_os.workflows.onboarding_path import generate_onboarding_path
from keprix.agent_os.workflows.outreach_agent import generate_outreach_package
from keprix.agent_os.workflows.seo_agent import generate_seo_package
from keprix.agent_os.workflows.video_agent import generate_video_package
from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


@pytest.fixture
def keprix_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / ".keprix"
    home.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    monkeypatch.setenv("KEPRIX_AUTO_SKILL_WRITE", "true")
    return home


def test_catalog_lists_phase4_templates() -> None:
    ids = {item["id"] for item in list_catalog_templates()}
    assert {"video-agent", "seo-agent", "outreach-agent", "onboarding-path"} <= ids


def test_video_agent_package() -> None:
    result = generate_video_package(topic="Agent OS", audience="operators", length_minutes=6)
    assert result["status"] == "ok"
    assert result["workflow"] == "video-agent"
    assert len(result["storyboard"]) >= 3
    assert "Video package: Agent OS" in result["output"]
    assert result["artifact"]["auto_skill"] is True


def test_seo_agent_package() -> None:
    result = generate_seo_package(keywords="agent os, vault memory", website="https://keprix.example")
    assert result["primary_keyword"] == "agent os"
    assert "SEO package" in result["output"]
    assert result["internal_links"]
    assert "keprix.example" in result["internal_links"][0]["suggested_url"]


def test_outreach_agent_package() -> None:
    result = generate_outreach_package(
        audience="agency owners",
        offer="a free Agent OS install",
        channels=["email", "linkedin"],
        days=10,
    )
    assert result["status"] == "ok"
    assert len(result["calendar"]) == 10
    assert result["followups"]
    assert result["lead_map"][0]["stage"] == "new"


def test_onboarding_path_package() -> None:
    result = generate_onboarding_path(product="Keprix", audience="solo founders")
    assert "Day 1" in result["output"]
    assert "Day 7" in result["output"]
    assert "Day 30" in result["output"]
    assert len(result["checklist"]["day_1"]) >= 3


def test_milestones_progress(keprix_home: Path) -> None:
    store = OnboardingProgressStore()
    store.complete_step("u1", "a1_provider")
    store.complete_step("u1", "a2_first_chat")
    payload = build_milestones(user_id="u1")
    assert payload["ok"] is True
    day1 = next(item for item in payload["milestones"] if item["id"] == "day_1")
    assert day1["done"] >= 2
    assert payload["current"]["id"] in {"day_1", "day_7", "day_30"}


def test_phase4_agent_apps_run(keprix_home: Path) -> None:
    video_dir = template_dir("video-agent")
    seo_dir = template_dir("seo-agent")
    assert video_dir and seo_dir
    video = run_local(video_dir, input_text="Launch video", context={"form": {"topic": "Launch video"}})
    assert video["result"]["status"] == "ok"
    seo = run_local(
        seo_dir,
        input_text="keprix install",
        context={"form": {"keywords": "keprix install", "website": "https://keprix.dev"}},
    )
    assert seo["result"]["status"] == "ok"
    assert "keprix install" in seo["result"]["output"]


def test_milestones_route(keprix_home: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)
    response = client.get("/api/agent-os/milestones")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["milestones"]) == 3
    onboarding = client.get("/api/agent-os/onboarding")
    assert onboarding.status_code == 200
    assert "milestones" in onboarding.json()
