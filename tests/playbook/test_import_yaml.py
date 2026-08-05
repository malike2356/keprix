"""Studio YAML import and export route tests."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "playbooks" / "canvas"


@pytest.mark.asyncio
async def test_yaml_import_opens_canvas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    yaml_text = """
id: imported_yaml
name: Imported YAML
entry: first
steps:
  - id: first
    type: agent_task
    prompt: Say hi
edges: []
"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/playbooks/studio/import/yaml", json={"yaml": yaml_text})

    assert response.status_code == 200
    assert response.json()["canvas"]["nodes"][1]["id"] == "first"


@pytest.mark.asyncio
async def test_export_zip_contains_yaml_and_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    canvas = json.loads((FIXTURES / "linear_three_node.json").read_text(encoding="utf-8"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.put("/api/playbooks/studio/daily_digest", json={"canvas": canvas})
        response = await client.get("/api/playbooks/studio/daily_digest/export")

    assert response.status_code == 200
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        assert "daily_digest.yaml" in archive.namelist()
        assert "daily_digest.layout.json" in archive.namelist()
        assert "README.txt" in archive.namelist()
