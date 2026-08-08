# Keprix - Prompt 188: STT API on Main Backend (Port 3333)

## Context

Web workspace uses `http://localhost:3333` (`frontend/src/lib/ce-api.ts`). Desktop transcribe exists only on `keprix_cli/web_server.py`. This prompt **extracts and mounts** the transcribe route on the main FastAPI app so the Next.js UI can call it with the same auth token as chat.

Depends on **187**.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Shared audio routes module

Create `src/keprix/api/audio_routes.py`:

```python
router = APIRouter(prefix="/api/audio", tags=["audio"])

class AudioTranscriptionRequest(BaseModel):
    data_url: str
    mime_type: str | None = None

@router.post("/transcribe")
async def transcribe_audio_upload(
    payload: AudioTranscriptionRequest,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ...
```

**Implementation rules:**

- Move logic from `web_server.py` `transcribe_audio_upload` (base64 data URL validation, size cap, temp file, `transcribe_audio` call). Do not duplicate; extract once.
- Require `get_current_user` (or `require_api_auth`) so anonymous browsers cannot burn STT quota.
- If `stt.enabled` is false in loaded config, return `403` with `{ "detail": "Speech-to-text is disabled" }`.
- Response shape (match desktop Hermes contract):

```json
{
  "ok": true,
  "transcript": "user speech as text",
  "provider": "local"
}
```

- Max upload size: reuse `_MAX_TRANSCRIPTION_UPLOAD_BYTES` from web_server (extract to `src/keprix/api/audio_limits.py` or constants module).

## Step 2: STT config helper

Create `src/keprix/api/stt_config.py`:

```python
def stt_enabled() -> bool:
    ...

def max_recording_seconds() -> int:
    # from config voice.max_recording_seconds, default 120
```

Load via `keprix_cli/config.py` `load_config()` (same path gateway uses).

## Step 3: Mount on main app

In `src/keprix/api/server.py`:

```python
from keprix.api.audio_routes import router as audio_router
app.include_router(audio_router)
```

## Step 4: Keep web_server working

Refactor `keprix_cli/web_server.py` to import and mount the same router (or call shared handler). Desktop Hermes must not break.

## Step 5: Public status endpoint (optional but recommended)

`GET /api/audio/status` (auth optional):

```json
{
  "stt_enabled": true,
  "provider": "local",
  "max_recording_seconds": 120,
  "transcribe_path": "/api/audio/transcribe"
}
```

Frontend uses this to hide/disable mic when STT is off.

## Tests

`tests/api/test_audio_transcribe.py`:

| Test | Expect |
| --- | --- |
| POST without auth | 401 |
| POST with invalid data_url | 400 |
| POST when stt.enabled=false | 403 |
| POST with valid tiny wav fixture (mock `transcribe_audio`) | 200 + transcript |
| Response includes provider field | |

Use monkeypatch on `transcribe_audio`; do not require faster-whisper in CI.

`tests/keprix_cli/test_web_server.py`: existing transcribe tests still pass after refactor.

## Docs

Update `docs/reference/api.md` with:

- `POST /api/audio/transcribe`
- `GET /api/audio/status`

## Acceptance criteria

- `curl -H "Authorization: Bearer $TOKEN" -X POST http://localhost:3333/api/audio/transcribe ...` works
- Desktop app transcribe unchanged
- No duplicate transcribe implementation bodies in web_server and audio_routes
- All new tests pass via `scripts/run_tests.sh tests/api/test_audio_transcribe.py`
