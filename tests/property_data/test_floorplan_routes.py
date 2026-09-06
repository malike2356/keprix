from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from keprix.property_floorplan import routes


@pytest.mark.asyncio
async def test_floorplan_upload_is_quarantined_and_removed(monkeypatch, tmp_path):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path / "data"))
    seen: list[str] = []

    def fake_analyze(path: str, **kwargs):
        seen.append(path)
        assert Path(path).is_file()
        return {"status": "complete", "proposed_rooms": [], "proposal_only": True}

    monkeypatch.setattr(routes, "analyze_image", fake_analyze)
    upload = UploadFile(filename="plan.png", file=__import__("io").BytesIO(b"png"), headers={"content-type": "image/png"})
    result = await routes.analyze_image_route(upload, _user={"id": "user-1"})

    assert result["proposal_only"] is True
    assert seen and not Path(seen[0]).exists()


@pytest.mark.asyncio
async def test_floorplan_upload_rate_limit_fails_closed(monkeypatch):
    monkeypatch.setattr("keprix.security.rate_limiter.rate_limit", lambda *args, **kwargs: False)
    upload = UploadFile(filename="plan.png", file=__import__("io").BytesIO(b"png"), headers={"content-type": "image/png"})
    with pytest.raises(HTTPException) as error:
        await routes.analyze_image_route(upload, _user={"id": "user-1"})
    assert error.value.status_code == 429
