"""Visual Playbook Studio route tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "playbooks" / "canvas"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_list_empty_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/playbooks/studio")

    assert response.status_code == 200
    assert response.json() == {"playbooks": []}


@pytest.mark.asyncio
async def test_put_save_and_get_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    canvas = _fixture("linear_three_node.json")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        save = await client.put("/api/playbooks/studio/daily_digest", json={"canvas": canvas})
        get = await client.get("/api/playbooks/studio/daily_digest")

    assert save.status_code == 200
    assert save.json() == {"saved": True, "compile_errors": []}
    assert get.status_code == 200
    payload = get.json()
    assert payload["yaml"]["id"] == "daily_digest"
    assert payload["canvas"]["nodes"][1]["id"] == "summarize"
    assert payload["layout"]["positions"]["summarize"] == {"x": 320, "y": 120}


@pytest.mark.asyncio
async def test_compile_422_on_invalid_canvas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/playbooks/studio/compile",
            json={"canvas": _fixture("invalid_missing_entry.json")},
        )

    assert response.status_code == 422
    codes = {error["code"] for error in response.json()["compile_errors"]}
    assert "missing_entry" in codes
