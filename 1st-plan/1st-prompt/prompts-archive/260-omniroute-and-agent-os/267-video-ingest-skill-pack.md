# Keprix - Prompt 267: Video ingest skill pack

**Series:** Chase five tools adoption **267-272**.  
**Master reference:** `../prompts-archive/ref-266-chase-five-tools-adoption-master-reference.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

A **video ingest skill pack** that extends `youtube-content` into full **local and remote video** handling with **frame extraction modes** (Chase "Claude Video" pattern).

Operators and agents can:

| Input | Output |
| --- | --- |
| YouTube URL | Transcript + optional frames (existing + extended) |
| Local MP4/MOV/WebM | Transcript (if captions embedded) + extracted frames |
| Remote video URL | Download to temp, same pipeline |

**Frame modes** (operator-selectable):

| Mode | Behavior |
| --- | --- |
| `caption-only` | Transcript only; no frames |
| `sparse` | 1 frame per N minutes (default N=5) |
| `balanced` | Scene-change heuristic + cap (default max 12 frames) |
| `dense` | Fixed interval (default every 30s, max 40 frames) |

Frames land in `{KEPRIX_HOME}/ingest/video/{job_id}/frames/` and are referenced in a manifest JSON for `vision_analyze` and **258** raw ingest.

**Non-goals:**

- No AI video generation
- No Gemini-only routing (multi-provider via existing vision stack)
- No Claude Code marketplace install flow

---

## 2. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| YouTube transcripts | `skills/media/youtube-content/` |
| Vision analysis | `vision_analyze` tool |
| FFmpeg in optional skills | `kanban-video-orchestrator` references |
| Competitor transcript pipeline | `planning/competitor-research/youtube-*` |

---

## 3. Architecture

```text
video-ingest skill (Hub optional-skills/media/)
        |
        v
scripts/ingest_video.py  (ffmpeg + yt-dlp + caption extract)
        |
        v
VideoIngestJob manifest JSON
        |
        +--> vision_analyze (per frame or batch question)
        +--> POST /api/ingest/video (optional API for UI)
        +--> 258 raw/ folder copy hook (if vault configured)
```

---

## 4. Data model

```python
@dataclass
class VideoIngestJob:
    job_id: str
    source_type: str          # youtube | local | url
    source_ref: str           # URL or path
    mode: str                 # caption-only | sparse | balanced | dense
    transcript_text: str | None
    transcript_path: str | None
    frames: list[dict]        # { path, timestamp_sec, label? }
    manifest_path: str
    created_at: str
    status: str               # pending | running | done | failed
    error: str | None
```

Persist under `{KEPRIX_HOME}/ingest/video/{job_id}/manifest.json`.

---

## 5. API routes (optional but recommended)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/ingest/video` | `{ source, mode?, copy_to_vault? }` start job |
| GET | `/api/ingest/video/{job_id}` | Job status + manifest |
| GET | `/api/ingest/video` | List recent jobs |

Feature flag: `video_ingest.enabled` (default true).

---

## 6. Skill surface

**Skill slug:** `video-ingest` (optional-skills; related to `youtube-content`)

**SKILL.md** documents:

- When to use vs `youtube-content` (YouTube-only vs any video)
- Frame mode selection guidance
- `uv` deps: `yt-dlp`, `ffmpeg` (system binary check)
- Example: ingest competitor MP4, run `vision_analyze` on key frames, write summary to vault

**CLI:**

```bash
keprix ingest video --url "https://youtube.com/watch?v=..." --mode balanced
keprix ingest video --file ./demo.mp4 --mode sparse
keprix ingest video list
keprix ingest video show <job_id>
```

---

## 7. UI (minimal)

`/ingest/video` page:

- Source picker (URL, file upload, YouTube paste)
- Mode dropdown
- Job list with status
- "Analyze frames" shortcut that opens chat with manifest context

Nav: **Ingest > Video** (or under Hub if preferred).

---

## 8. Files to create

```
src/keprix/ingest/
  __init__.py
  video_ingest_service.py
  video_job_store.py
  frame_extractor.py

src/keprix/api/
  video_ingest_routes.py

src/keprix/optional-skills/media/video-ingest/
  SKILL.md
  scripts/ingest_video.py

frontend/src/app/(workspace)/ingest/video/page.tsx

docs/features/video-ingest.md

tests/ingest/
  test_video_ingest_service.py
  test_frame_extractor.py
  test_video_ingest_routes.py
```

Wire routes in existing API router pattern. Register CLI in `keprix_cli/main.py`.

---

## 9. Acceptance criteria

- YouTube URL ingests with all four frame modes; `caption-only` produces zero frame files.
- Local MP4 test fixture ingests with at least one frame in `balanced` mode.
- Manifest JSON lists transcript path and frame paths with timestamps.
- `vision_analyze` can consume frame paths from manifest (documented in SKILL.md).
- Failed ffmpeg/yt-dlp runs set `status=failed` with error message (no silent success).
- API + CLI share same job store.
- Tests use mocked ffmpeg for unit tests; one integration test with tiny fixture if feasible.

---

## 10. Dependencies

- **Soft:** **258** vault raw folder copy
- **Parallel:** **268** notebook bridge may consume video summaries
- **Next in pack:** **269** graphiti can ingest manifest summaries
