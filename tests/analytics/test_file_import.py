"""Tests for analytics file import."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.analytics.file_import import AnalyticsImportError, parse_analytics_file
from keprix.api.main import app


def test_parse_csv_file() -> None:
    content = b"name,score\nAlice,85\nBob,92\n"
    result = parse_analytics_file("scores.csv", content)
    assert result["tabular"] is True
    assert result["row_count"] == 2
    assert "Alice,85" in result["data"]


def test_parse_json_array_to_csv() -> None:
    payload = [{"name": "Alice", "score": 85}, {"name": "Bob", "score": 92}]
    result = parse_analytics_file("scores.json", json.dumps(payload).encode())
    assert result["source_type"] == "json"
    assert "name,score" in result["data"]
    assert result["row_count"] == 2


def test_parse_tsv_file() -> None:
    content = b"name\tscore\nAlice\t85\n"
    result = parse_analytics_file("scores.tsv", content)
    assert "Alice,85" in result["data"]


def test_unsupported_extension_raises() -> None:
    with pytest.raises(AnalyticsImportError, match="Unsupported"):
        parse_analytics_file("data.zip", b"binary")


def test_parse_sav_when_pyreadstat_available() -> None:
    pytest.importorskip("pyreadstat")
    import pyreadstat
    import pandas as pd

    frame = pd.DataFrame({"name": ["Alice", "Bob"], "score": [85, 92]})
    sav_path = "/tmp/keprix-test-export.sav"
    pyreadstat.write_sav(frame, sav_path)
    try:
        content = Path(sav_path).read_bytes()
        result = parse_analytics_file("scores.sav", content)
        assert result["source_type"] == "spss"
        assert "Alice" in result["data"]
    finally:
        Path(sav_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_parse_file_route(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    headers = {"Authorization": "Bearer test-api-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/analytics/parse-file",
            headers=headers,
            files={"file": ("demo.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["filename"] == "demo.csv"
        assert body["row_count"] == 1
        assert "a,b" in body["data"]
