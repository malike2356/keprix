"""Prompt 267 frame extraction tests."""

from __future__ import annotations

from pathlib import Path
import subprocess

from keprix.ingest.frame_extractor import FrameExtractor


def test_caption_only_returns_no_frames(tmp_path: Path) -> None:
    source = tmp_path / "demo.mp4"
    source.write_bytes(b"fake")

    frames = FrameExtractor().extract(source, tmp_path / "frames", mode="caption-only")

    assert frames == []


def test_dense_mode_uses_ffmpeg_and_manifest_paths(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "demo.mp4"
    source.write_bytes(b"fake")
    calls: list[list[str]] = []

    monkeypatch.setattr("keprix.ingest.frame_extractor.shutil.which", lambda name: f"/usr/bin/{name}")

    def fake_run(cmd, capture_output, text, check):
        calls.append(cmd)
        if cmd[0] == "ffprobe":
            return subprocess.CompletedProcess(cmd, 0, stdout='{"format": {"duration": "65.0"}}', stderr="")
        Path(cmd[-1]).write_bytes(b"jpg")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("keprix.ingest.frame_extractor.subprocess.run", fake_run)

    frames = FrameExtractor().extract(source, tmp_path / "frames", mode="dense", dense_interval_sec=30)

    assert [frame["timestamp_sec"] for frame in frames] == [0.0, 30.0, 60.0]
    assert all(Path(frame["path"]).exists() for frame in frames)
    assert any(cmd[0] == "ffmpeg" for cmd in calls)


def test_balanced_mode_uses_scene_extraction(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "demo.mp4"
    source.write_bytes(b"fake")

    monkeypatch.setattr("keprix.ingest.frame_extractor.shutil.which", lambda name: f"/usr/bin/{name}")

    def fake_run(cmd, capture_output, text, check):
        if cmd[0] == "ffprobe":
            return subprocess.CompletedProcess(cmd, 0, stdout='{"format": {"duration": "120.0"}}', stderr="")
        if "select='gt(scene,0.35)'" in cmd:
            output_pattern = Path(cmd[-1])
            (output_pattern.parent / "scene_001.jpg").write_bytes(b"jpg")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr("keprix.ingest.frame_extractor.subprocess.run", fake_run)

    frames = FrameExtractor().extract(source, tmp_path / "frames", mode="balanced", balanced_max_frames=12)

    assert len(frames) == 1
    assert frames[0]["label"] == "scene 1"
