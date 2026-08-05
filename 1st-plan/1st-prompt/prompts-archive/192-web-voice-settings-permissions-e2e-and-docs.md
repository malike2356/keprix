# Keprix - Prompt 192: Web Voice Settings, Permissions, E2E, and Docs

## Context

Finish voice input for production: settings surfacing, security notes, end-to-end verification, and operator docs.

Depends on **191**.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Settings UI stub (read-only v1)

Add section to `frontend/src/app/(workspace)/settings/page.tsx` or new `settings/voice/page.tsx`:

| Field | Source |
| --- | --- |
| Speech-to-text | `GET /api/audio/status` -> enabled/disabled |
| Provider | status.provider |
| Max recording | status.max_recording_seconds |
| Link | "STT is configured in Keprix config.yaml under `stt`" |

No inline edit in v1 (per Keprix AGENTS.md: behavioral config in config.yaml, not new env vars in UI).

Optional: link to docs `docs/configuration/environment-variables.md` for API keys (Groq, OpenAI) used by STT providers.

## Step 2: HTTPS and deployment notes

Update `docs/features/web-voice-input.md`:

- `getUserMedia` requires secure context (HTTPS or localhost)
- Reverse proxy must not strip multipart/audio
- Recommended max recording aligns with `voice.max_recording_seconds`

## Step 3: Security and abuse

In `docs/security/architecture.md` (short subsection):

- Transcribe endpoint auth required
- Rate limit: add to existing `RateLimitMiddleware` for `POST /api/audio/transcribe` (e.g. 30/hour per user in community edition, configurable later)
- Audio temp files deleted after transcribe (already in handler)

Implement rate limit in `src/keprix/api/audio_routes.py` or middleware if not present.

## Step 4: UI contract (optional)

If workspace exposes feature flags via `build_ui_contract`, add:

```python
"voice_input": stt_enabled(),
```

Frontend hides mic when false (belt and suspenders with status endpoint).

## Step 5: E2E test

`tests/e2e/test_web_voice_transcribe.py` (or extend existing API e2e):

1. Auth fixture
2. POST small valid base64 audio sample with mocked `transcribe_audio`
3. Assert 200 and transcript field

`frontend` Vitest integration optional if Playwright not in repo; API e2e is minimum.

## Step 6: Archive prompts

When 187-192 complete:

- Move `187-*.md` through `192-*.md` to `planning/prompts/prompts-archive/`
- Update `PROMPT-IMPLEMENTATION-AUDIT.md`
- Update `pending-prompts/README.md`

## Step 7: User-facing docs

`docs/features/web-voice-input.md` complete sections:

- How to use mic in chat
- Troubleshooting (permission denied, STT disabled, empty transcript)
- Provider setup (local faster-whisper vs Groq API key)
- Difference vs desktop voice conversation mode

`docs/index.md`: link under Features.

## Step 8: Writing style scan

Run from repo root:

```bash
python3 scripts/fix-writing-style.py --check docs/features/web-voice-input.md
```

## Acceptance criteria

- Rate limit on transcribe endpoint (test proves 429 after threshold with low limit in test config)
- Settings page shows STT status from API
- E2E/API test passes
- Docs linked from docs index
- Full flow works on Chrome + Firefox (manual checklist in PR)
- Prompts 187-192 archived

## Out of scope (future prompts)

- Hold-to-talk (mouse down/up)
- Continuous voice conversation in web (desktop parity)
- TTS read-aloud on assistant messages in web chat
- Wake word in browser
- Offline-only WASM whisper in browser (server STT is v1)

## Launch checklist

- [ ] `stt.enabled: true` in default dev config
- [ ] faster-whisper or Groq key documented for devs
- [ ] Mic visible on `/chat/*`
- [ ] Error states QA'd
- [ ] No em dashes in new docs
