"""ffmpeg-backed frame extraction for video ingest."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any


FRAME_MODES = {"caption-only", "sparse", "balanced", "dense"}


class FrameExtractionError(RuntimeError):
    pass


class FrameExtractor:
    def __init__(self, *, ffmpeg_bin: str = "ffmpeg", ffprobe_bin: str = "ffprobe") -> None:
        self.ffmpeg_bin = ffmpeg_bin
        self.ffprobe_bin = ffprobe_bin

    def ensure_available(self) -> None:
        if shutil.which(self.ffmpeg_bin) is None:
            raise FrameExtractionError("ffmpeg is not installed or is not on PATH")

    def probe_duration(self, source: Path) -> float:
        cmd = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(source),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise FrameExtractionError(result.stderr.strip() or "ffprobe failed")
        try:
            return max(float(json.loads(result.stdout)["format"]["duration"]), 0.1)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise FrameExtractionError("ffprobe did not return a duration") from exc

    def extract(
        self,
        source: Path,
        output_dir: Path,
        *,
        mode: str,
        sparse_minutes: int = 5,
        dense_interval_sec: int = 30,
        balanced_max_frames: int = 12,
        dense_max_frames: int = 40,
    ) -> list[dict[str, Any]]:
        if mode not in FRAME_MODES:
            raise ValueError(f"unknown frame mode: {mode}")
        if mode == "caption-only":
            return []
        self.ensure_available()
        output_dir.mkdir(parents=True, exist_ok=True)
        duration = self.probe_duration(source)
        if mode == "balanced":
            frames = self._extract_balanced(source, output_dir, duration, balanced_max_frames)
            if frames:
                return frames
            return self._extract_at_timestamps(source, output_dir, [min(duration / 2, max(duration - 0.1, 0))])
        interval = sparse_minutes * 60 if mode == "sparse" else dense_interval_sec
        max_frames = balanced_max_frames if mode == "sparse" else dense_max_frames
        timestamps = self._timestamps(duration, interval, max_frames)
        return self._extract_at_timestamps(source, output_dir, timestamps)

    def _timestamps(self, duration: float, interval: int, max_frames: int) -> list[float]:
        interval = max(interval, 1)
        if duration <= interval:
            return [0.0]
        timestamps: list[float] = []
        current = 0.0
        while current < duration and len(timestamps) < max_frames:
            timestamps.append(round(current, 3))
            current += interval
        return timestamps

    def _extract_at_timestamps(self, source: Path, output_dir: Path, timestamps: list[float]) -> list[dict[str, Any]]:
        frames: list[dict[str, Any]] = []
        for index, timestamp in enumerate(timestamps, start=1):
            target = output_dir / f"frame_{index:03d}.jpg"
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-ss",
                str(timestamp),
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(target),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise FrameExtractionError(result.stderr.strip() or "ffmpeg frame extraction failed")
            if target.exists():
                frames.append({"path": str(target), "timestamp_sec": timestamp, "label": f"{timestamp:.1f}s"})
        return frames

    def _extract_balanced(self, source: Path, output_dir: Path, duration: float, max_frames: int) -> list[dict[str, Any]]:
        target_pattern = output_dir / "scene_%03d.jpg"
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(source),
            "-vf",
            "select='gt(scene,0.35)'",
            "-vsync",
            "vfr",
            "-frames:v",
            str(max_frames),
            "-q:v",
            "2",
            str(target_pattern),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise FrameExtractionError(result.stderr.strip() or "ffmpeg scene extraction failed")
        paths = sorted(output_dir.glob("scene_*.jpg"))[:max_frames]
        if not paths:
            return []
        step = duration / (len(paths) + 1)
        return [
            {"path": str(path), "timestamp_sec": round(step * (index + 1), 3), "label": f"scene {index + 1}"}
            for index, path in enumerate(paths)
        ]
