# Video ingest

Video ingest turns YouTube URLs, direct video URLs, and local MP4/MOV/WebM files into a manifest with transcript text and optional extracted frames.

Manifests live at:

```text
{KEPRIX_HOME}/ingest/video/<job_id>/manifest.json
```

Frames live beside the manifest under `frames/` and are ready for `vision_analyze`.

## Frame modes

| Mode | Behavior |
| --- | --- |
| `caption-only` | Fetch transcript or sidecar captions only; no frame files |
| `sparse` | Extract one frame every N minutes |
| `balanced` | Extract scene-change frames capped to a small set |
| `dense` | Extract fixed interval frames for fast visual demos |

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/ingest/video` | Ingest `{ source, mode, copy_to_vault }` |
| `GET` | `/api/ingest/video` | List recent jobs |
| `GET` | `/api/ingest/video/{job_id}` | Fetch one manifest |

Set `KEPRIX_VIDEO_INGEST_ENABLED=0` to disable these routes.

## CLI

```bash
keprix ingest video --url "https://youtube.com/watch?v=..." --mode balanced
keprix ingest video --file ./demo.mp4 --mode sparse
keprix ingest video list
keprix ingest video show <job_id>
```

Install optional dependencies with `uv pip install yt-dlp youtube-transcript-api` and install the `ffmpeg` system binary for frame extraction.
