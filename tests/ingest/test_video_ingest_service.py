"""Prompt 267 video ingest service tests."""

from __future__ import annotations

from pathlib import Path

from keprix.ingest.video_ingest_service import VideoIngestService


class StubExtractor:
    def extract(self, source, output_dir, **kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        frame = output_dir / "frame_001.jpg"
        frame.write_bytes(b"jpg")
        return [{"path": str(frame), "timestamp_sec": 0.0, "label": "0.0s"}]


def test_local_video_balanced_manifest_includes_transcript_and_frame(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    source = tmp_path / "demo.mp4"
    source.write_bytes(b"fake")
    source.with_suffix(".txt").write_text("Transcript text", encoding="utf-8")

    job = VideoIngestService(extractor=StubExtractor()).ingest(str(source), mode="balanced")

    assert job.status == "done"
    assert job.transcript_path
    assert job.transcript_text == "Transcript text"
    assert len(job.frames) == 1
    assert Path(job.manifest_path).is_file()


def test_caption_only_youtube_produces_zero_frames(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setattr(VideoIngestService, "_youtube_transcript", lambda self, source: "0.0 hello")

    job = VideoIngestService(extractor=StubExtractor()).ingest("https://youtube.com/watch?v=abcdefghijk", mode="caption-only")

    assert job.status == "done"
    assert job.source_type == "youtube"
    assert job.frames == []
    assert job.transcript_text == "0.0 hello"


def test_frame_failure_sets_failed_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    source = tmp_path / "demo.mp4"
    source.write_bytes(b"fake")

    class FailingExtractor:
        def extract(self, source, output_dir, **kwargs):
            raise RuntimeError("ffmpeg exploded")

    job = VideoIngestService(extractor=FailingExtractor()).ingest(str(source), mode="sparse")

    assert job.status == "failed"
    assert "ffmpeg exploded" in (job.error or "")
