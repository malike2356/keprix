---
name: video-ingest
description: Ingest YouTube, remote, or local videos into transcript and frame manifests for vision analysis and workspace raw folders.
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [video, ingest, frames, ffmpeg, youtube]
    related_skills: [youtube-content]
---

# Video Ingest

Use this skill when the user gives a YouTube URL, a direct video URL, or a local MP4/MOV/WebM path and wants transcript plus selected frames for analysis.

Use `youtube-content` instead when the request is only to fetch or summarize a YouTube transcript and no frames are needed.

## Setup

Install optional tools:

```bash
uv pip install yt-dlp youtube-transcript-api
```

Install `ffmpeg` on the system path. Frame extraction and embedded subtitle extraction use the `ffmpeg` and `ffprobe` binaries.

## Frame modes

| Mode | Use |
| --- | --- |
| `caption-only` | Transcript only; no frames |
| `sparse` | Long talks where one frame every few minutes is enough |
| `balanced` | Default; scene-change extraction capped to key frames |
| `dense` | Short UI demos or fast visual changes |

## Commands

```bash
keprix ingest video --url "https://youtube.com/watch?v=VIDEO_ID" --mode balanced
keprix ingest video --file ./demo.mp4 --mode sparse
keprix ingest video list
keprix ingest video show <job_id>
```

The helper script wraps the same service:

```bash
uv run python3 SKILL_DIR/scripts/ingest_video.py --url "https://example.com/demo.mp4" --mode dense
```

Manifests are written to `{KEPRIX_HOME}/ingest/video/<job_id>/manifest.json`. Frame paths in that manifest can be passed to `vision_analyze`; ask a question per frame or batch useful frames into one visual inspection task.

Use `--copy-to-vault` when the configured vault is a local folder and the source should also appear under `raw/video/<job_id>/`.
