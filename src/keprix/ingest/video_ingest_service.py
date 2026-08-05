"""Video ingest service for local, remote, and YouTube sources."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import urllib.parse
import urllib.request

from keprix.ingest.frame_extractor import FRAME_MODES, FrameExtractionError, FrameExtractor
from keprix.ingest.video_job_store import VideoIngestJob, VideoJobStore


class VideoIngestError(RuntimeError):
    pass


YOUTUBE_RE = re.compile(r"(youtube\.com|youtu\.be)", re.IGNORECASE)


def video_ingest_enabled() -> bool:
    import os

    return os.getenv("KEPRIX_VIDEO_INGEST_ENABLED", "1").lower() not in {"0", "false", "no"}


def detect_source_type(source: str) -> str:
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme in {"http", "https"}:
        return "youtube" if YOUTUBE_RE.search(source) else "url"
    return "local"


class VideoIngestService:
    def __init__(self, store: VideoJobStore | None = None, extractor: FrameExtractor | None = None) -> None:
        self.store = store or VideoJobStore()
        self.extractor = extractor or FrameExtractor()

    def ingest(
        self,
        source: str,
        *,
        mode: str = "balanced",
        copy_to_vault: bool = False,
        sparse_minutes: int = 5,
        dense_interval_sec: int = 30,
        max_frames: int | None = None,
    ) -> VideoIngestJob:
        if mode not in FRAME_MODES:
            raise ValueError(f"unknown frame mode: {mode}")
        source_type = detect_source_type(source)
        job = self.store.create(source_type=source_type, source_ref=source, mode=mode)
        job.status = "running"
        self.store.save(job)
        try:
            job_dir = self.store.job_dir(job.job_id)
            local_source = self._resolve_source(source, source_type, job_dir, mode)
            job.local_source_path = str(local_source) if local_source else None
            transcript = self._extract_transcript(source, source_type, local_source, job_dir)
            if transcript:
                transcript_path = job_dir / "transcript.txt"
                transcript_path.write_text(transcript, encoding="utf-8")
                job.transcript_text = transcript
                job.transcript_path = str(transcript_path)
            if mode != "caption-only":
                if local_source is None:
                    raise VideoIngestError("frame extraction requires a local video file")
                cap = max_frames or (40 if mode == "dense" else 12)
                job.frames = self.extractor.extract(
                    local_source,
                    job_dir / "frames",
                    mode=mode,
                    sparse_minutes=sparse_minutes,
                    dense_interval_sec=dense_interval_sec,
                    balanced_max_frames=cap,
                    dense_max_frames=cap,
                )
            if copy_to_vault:
                job.vault_copy_path = self._copy_to_vault(job)
            job.status = "done"
            job.error = None
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
        return self.store.save(job)

    def _resolve_source(self, source: str, source_type: str, job_dir: Path, mode: str) -> Path | None:
        if source_type == "local":
            path = Path(source).expanduser()
            if not path.is_file():
                raise VideoIngestError(f"local video not found: {source}")
            return path.resolve()
        if source_type == "youtube":
            if mode == "caption-only":
                return None
            return self._download_with_ytdlp(source, job_dir)
        return self._download_url(source, job_dir)

    def _download_with_ytdlp(self, source: str, job_dir: Path) -> Path:
        if shutil.which("yt-dlp") is None:
            raise VideoIngestError("yt-dlp is not installed or is not on PATH")
        output_template = str(job_dir / "source.%(ext)s")
        result = subprocess.run(
            ["yt-dlp", "-f", "mp4/bestvideo+bestaudio/best", "-o", output_template, source],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise VideoIngestError(result.stderr.strip() or "yt-dlp download failed")
        candidates = [path for path in job_dir.glob("source.*") if path.is_file()]
        if not candidates:
            raise VideoIngestError("yt-dlp completed without a downloaded video")
        return candidates[0]

    def _download_url(self, source: str, job_dir: Path) -> Path:
        suffix = Path(urllib.parse.urlparse(source).path).suffix or ".mp4"
        target = job_dir / f"source{suffix}"
        try:
            urllib.request.urlretrieve(source, target)
        except Exception as exc:
            raise VideoIngestError(f"remote video download failed: {exc}") from exc
        return target

    def _extract_transcript(self, source: str, source_type: str, local_source: Path | None, job_dir: Path) -> str | None:
        if source_type == "youtube":
            return self._youtube_transcript(source)
        if local_source is None:
            return None
        sidecar = self._sidecar_transcript(local_source)
        if sidecar:
            return sidecar
        return self._embedded_subtitles(local_source, job_dir)

    def _youtube_transcript(self, source: str) -> str | None:
        try:
            from keprix.skills.media.youtube_content.scripts.fetch_transcript import extract_video_id  # type: ignore[import-not-found]
        except Exception:
            extract_video_id = self._extract_youtube_id
        video_id = extract_video_id(source)
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            result = YouTubeTranscriptApi().fetch(video_id)
            return "\n".join(f"{snippet.start:.2f} {snippet.text}" for snippet in result)
        except Exception:
            return None

    def _extract_youtube_id(self, source: str) -> str:
        patterns = [
            r"(?:v=|youtu\.be/|shorts/|embed/|live/)([a-zA-Z0-9_-]{11})",
            r"^([a-zA-Z0-9_-]{11})$",
        ]
        for pattern in patterns:
            match = re.search(pattern, source)
            if match:
                return match.group(1)
        return source

    def _sidecar_transcript(self, local_source: Path) -> str | None:
        for suffix in (".txt", ".vtt", ".srt"):
            path = local_source.with_suffix(suffix)
            if path.is_file():
                return path.read_text(encoding="utf-8")
        return None

    def _embedded_subtitles(self, local_source: Path, job_dir: Path) -> str | None:
        if shutil.which("ffmpeg") is None:
            return None
        target = job_dir / "embedded-subtitles.srt"
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(local_source), "-map", "0:s:0", str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not target.is_file():
            return None
        return target.read_text(encoding="utf-8")

    def _copy_to_vault(self, job: VideoIngestJob) -> str | None:
        try:
            from keprix.vault.config import get_vault_config

            config = get_vault_config()
        except Exception:
            return None
        if config.provider != "local_folder" or not config.root_path:
            return None
        target = Path(config.root_path) / "raw" / "video" / job.job_id
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(job.manifest_path, target / "manifest.json")
        if job.transcript_path:
            shutil.copy2(job.transcript_path, target / "transcript.txt")
        return str(target)
