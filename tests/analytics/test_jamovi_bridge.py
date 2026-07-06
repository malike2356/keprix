"""jamovi bridge tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.analytics.jamovi.analysis_plan import build_analysis_plan
from keprix.analytics.jamovi.export_bridge import prepare_export_package
from keprix.analytics.jamovi.r_syntax import plan_to_r_script
from keprix.api.main import app


def test_prepare_export_package() -> None:
    package = prepare_export_package(
        [{"age": 30, "score": 88}, {"age": 25, "score": 91}],
        columns=[{"name": "age"}, {"name": "score", "label": "Score"}],
        dataset_name="survey",
    )
    assert "data.csv" in package["csv"] or "age" in package["csv"]
    assert package["metadata"]["dataset_name"] == "survey"
    assert package["package_bytes"].startswith(b"PK")


def test_analysis_plan_and_r_script() -> None:
    plan = build_analysis_plan(
        dataset_name="survey",
        variables=["score", "group"],
        analysis="regression",
    )
    script = plan_to_r_script(plan)
    assert "lm(" in script


@pytest.mark.asyncio
async def test_jamovi_routes(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        modules = await client.get("/api/analytics/jamovi/modules", headers=headers)
        assert modules.status_code == 200
        assert len(modules.json()["modules"]) >= 4

        exported = await client.post(
            "/api/analytics/jamovi/export",
            headers=headers,
            json={"rows": [{"x": 1, "y": 2}], "dataset_name": "demo"},
        )
        assert exported.status_code == 200
        assert exported.json()["dataset_name"] == "demo"
