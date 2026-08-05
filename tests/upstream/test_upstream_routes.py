"""API tests for upstream admin routes."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.api.upstream_routes import router
from keprix.upstream.hermes_monitor import AdoptionStatus, FeatureCategory, UpstreamFeature


@pytest.fixture
def inventory_path(tmp_path: Path) -> Path:
    path = tmp_path / "inventory.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "processed_versions": ["0.17.0"],
                "keprix_features": {},
                "tracked_features": {
                    "hermes-0.18.0-abc": UpstreamFeature(
                        feature_id="hermes-0.18.0-abc",
                        name="Browser tool",
                        description="New browser automation MCP tool",
                        category=FeatureCategory.TOOL,
                        version_introduced="0.18.0",
                        release_date="2026-07-09T12:00:00Z",
                        release_url="https://example.test",
                        adoption_status=AdoptionStatus.UNEVALUATED,
                        suggested_status=AdoptionStatus.ADOPT_WITH_HARDENING,
                    ).to_dict()
                },
                "next_prompt_number": 600,
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def client(inventory_path: Path, monkeypatch):
    app = FastAPI()
    app.include_router(router)

    async def _admin():
        return {"id": "admin", "role": "admin"}

    app.dependency_overrides[__import__("keprix.auth.dependencies", fromlist=["require_admin"]).require_admin] = _admin

    from keprix.api import upstream_routes

    monkeypatch.setattr(upstream_routes, "_monitor", lambda: __import__("keprix.upstream.hermes_monitor", fromlist=["HermesMonitor"]).HermesMonitor(inventory_path))
    return TestClient(app)


def test_overview_and_decide(client: TestClient):
    response = client.get("/api/admin/upstream")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pending_count"] >= 1

    decide = client.post(
        "/api/admin/upstream/features/hermes-0.18.0-abc/decide",
        json={"status": "adopt_with_hardening", "notes": "ok"},
    )
    assert decide.status_code == 200
    assert decide.json()["feature"]["adoption_status"] == "adopt_with_hardening"


def test_adopt_after_decide(client: TestClient, tmp_path: Path, monkeypatch):
    from keprix.upstream.hermes_adoption import AdoptionPromptGenerator
    from keprix.api import upstream_routes

    decide = client.post(
        "/api/admin/upstream/features/hermes-0.18.0-abc/decide",
        json={"status": "adopt_with_hardening"},
    )
    assert decide.status_code == 200

    original = AdoptionPromptGenerator.generate

    def _generate(self, feature_id, *, require_approval=True):
        self.prompts_dir = tmp_path / "prompts"
        self.work_packages_dir = tmp_path / "work"
        return original(self, feature_id, require_approval=require_approval)

    monkeypatch.setattr(AdoptionPromptGenerator, "generate", _generate)
    adopt = client.post("/api/admin/upstream/features/hermes-0.18.0-abc/adopt")
    assert adopt.status_code == 200
    body = adopt.json()
    assert body["prompt_path"]
    assert body["work_package_path"]
