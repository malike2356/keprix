# Reference: Web voice input architecture (Prompt 187)

Orientation reference for the **187-192** prompt series. Executable prompts live in `pending-prompts/` until archived.

Operator doc: `docs/features/web-voice-input.md`.

## Problem statement

Workspace web chat has no microphone input. Desktop and gateway STT exist, but the Next.js UI cannot call transcribe on port **3333** today.

| Component | Status |
| --- | --- |
| `ChatInputBar.tsx` | Attach + mic + text + send (191 shipped) |
| `POST /api/audio/transcribe` | Main API :3333 (auth) + Hermes desktop (shared handler) |
| `GET /api/audio/status` | Main API :3333 |
| `transcription_tools.py` | Shared STT implementation |

## Product requirements (v1)

| Requirement | Detail |
| --- | --- |
| Interaction | Push-to-talk: click start, click stop |
| Flow | Record -> transcribe -> insert in composer -> user edits -> Send |
| Not in v1 | Always-on voice chat, web TTS auto-reply |
| Auth | Same session auth as workspace `/api/*` |
| Privacy | "Listening..." state; no upload while idle |
| Disable path | `stt.enabled: false` or mic denied -> disabled + help text |

## Architecture decision: MUI shell + shadcn voice island

**Approved**

1. Scoped Tailwind + shadcn under `frontend/src/components/ui/`
2. Tailwind `important: ".kp-voice-root"` (or equivalent prefix) to avoid MUI clashes
3. `ChatVoiceControl.tsx` bridges shadcn voice UI into MUI `ChatInputBar`

**Rejected**

- Full-app shadcn migration
- Rewriting `ChatInputBar` in shadcn

## Data flow

```text
[User clicks mic in AIVoiceInput]
        |
        v
[useWebVoiceRecorder: MediaRecorder -> Blob webm/opus]
        |
        v
[POST /api/audio/transcribe  (main API :3333)]
        |
        v
[tools.transcription_tools.transcribe_audio]
        |
        v
[transcript string -> ChatInputBar setValue / append]
        |
        v
[User sends via existing onSend -> useChat -> /api/conversations/...]
```

## Why transcribe moves to a shared router (Prompt 188)

1. **Single implementation:** Extract handler from `web_server.py`; mount same router on `server.py` and Hermes.
2. **Auth alignment:** Web workspace uses `ce-api.ts` Bearer tokens; Hermes desktop route is currently unauthenticated at the handler level.
3. **Feature flags:** `GET /api/audio/status` lets the UI hide the mic when `stt.enabled` is false.
4. **Tests:** `tests/api/test_audio_transcribe.py` targets port 3333 without spinning Hermes.

## Config surface

Existing `config.yaml` only (no new env vars for behavior):

```yaml
stt:
  enabled: true
  provider: local
voice:
  max_recording_seconds: 120
```

Defaults: `src/keprix/keprix_cli/config.py` (`stt` block ~line 1689, `voice.max_recording_seconds` 120).

Provider order: `stt.provider` key selects backend inside `transcribe_audio`; gateway and desktop use the same module.

## Browser matrix

| Browser | getUserMedia | MediaRecorder webm/opus |
| --- | --- | --- |
| Chrome / Edge | Yes | Yes |
| Firefox | Yes | Yes (verify codec) |
| Safari | Yes | Fallback mime may be required |

Production requires HTTPS (or localhost) for `getUserMedia`.

## Related systems

```text
                    transcription_tools.transcribe_audio
                                    ^
        +---------------------------+---------------------------+
        |                           |                           |
  web :3333                  Hermes web_server            messaging gateway
  (prompt 188)               (desktop transcribeAudio)      (voice messages)
        |
  Next.js useWebVoiceRecorder
  (prompt 190-191)
```

- **Desktop:** `use-voice-recorder.ts`, `transcribeAudio` in `apps/desktop/src/keprix.ts`
- **Gateway:** inbound voice attachments on Telegram, Discord, etc.
- **Web v1:** composer dictate only; not `useVoiceConversation`

## Prompt dependency chain

```text
187 (docs) -> 188 (API) -> 189 (UI island) -> 190 (hooks) -> 191 (ChatInputBar) -> 192 (settings, E2E, archive)
```

| # | File | Depends on |
| --- | --- | --- |
| 187 | `187-web-voice-input-orientation-and-architecture.md` | 136 |
| 188 | `188-web-voice-stt-api-main-backend.md` | 187 |
| 189 | `189-web-voice-shadcn-component-and-tailwind-island.md` | 187, 116 |
| 190 | `190-web-voice-recorder-hook-and-transcription-client.md` | 188, 189 |
| 191 | `191-web-voice-chat-composer-integration.md` | 189, 190, 136 | archived |
| 192 | `192-web-voice-settings-permissions-e2e-and-docs.md` | 191 | archived |

## Key file paths

| Path | Role |
| --- | --- |
| `frontend/src/components/workspace/ChatInputBar.tsx` | Integration point (191) |
| `frontend/src/lib/ce-api.ts` | API base :3333 + auth |
| `src/keprix/api/server.py` | Mount audio router (188) |
| `src/keprix/keprix_cli/web_server.py` | Existing transcribe (refactor 188) |
| `src/keprix/tools/transcription_tools.py` | STT providers |
| `frontend/src/components/ui/ai-voice-input.tsx` | shadcn component (189) |
| `frontend/src/hooks/useWebVoiceRecorder.ts` | Web recorder (190) |

## Acceptance (Prompt 187)

- [x] `docs/features/web-voice-input.md` with diagram and scope boundaries
- [x] Team decision recorded: shadcn island, not full-stack migration
- [x] Dependencies 188-192 listed in `pending-prompts/README.md`
- [x] No application code in this prompt
