"""Prompt 267 video ingest API tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


class StubExtractor:
    def extract(self, source, output_dir, **kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        frame = output_dir / "frame_001.jpg"
        frame.write_bytes(b"jpg")
        return [{"path": str(frame), "timestamp_sec": 0.0}]


def test_video_ingest_routes_share_job_store(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    source = tmp_path / "demo.mp4"
    source.write_bytes(b"fake")
    source.with_suffix(".txt").write_text("caption", encoding="utf-8")
    monkeypatch.setattr("keprix.api.video_ingest_routes.VideoIngestService", lambda: __import__("keprix.ingest.video_ingest_service", fromlist=["VideoIngestService"]).VideoIngestService(extractor=StubExtractor()))

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    created = client.post("/api/ingest/video", json={"source": str(source), "mode": "balanced"})
    assert created.status_code == 200
    job = created.json()["job"]
    assert job["status"] == "done"
    assert job["frames"]

    listed = client.get("/api/ingest/video")
    assert listed.status_code == 200
    assert listed.json()["jobs"][0]["job_id"] == job["job_id"]

    detail = client.get(f"/api/ingest/video/{job['job_id']}")
    assert detail.status_code == 200
    assert detail.json()["job"]["manifest_path"] == job["manifest_path"]


def test_video_ingest_feature_flag_blocks_routes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_VIDEO_INGEST_ENABLED", "0")
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    assert client.get("/api/ingest/video").status_code == 403
