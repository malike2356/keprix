# Keprix - Prompt 187: Web Voice Input Orientation and Architecture

## Context

The workspace web UI (`frontend/`, port 3000) has **no voice input** for chat. Users type only via `ChatInputBar.tsx`. The desktop app already supports dictate mode (`use-voice-recorder.ts`, `transcribeAudio` via Hermes). STT backends exist in `tools/transcription_tools.py` with `stt.*` config in `config.yaml`.

**Gap:** `POST /api/audio/transcribe` lives on `keprix_cli/web_server.py` (dashboard/Hermes) but **not** on the main FastAPI app (`src/keprix/api/server.py`, port 3333) that the Next.js workspace calls via `ce-api.ts`.

This prompt series (187-192) adds **push-to-talk voice input** in the web chat composer, using the supplied `AIVoiceInput` shadcn component (adapted for this repo).

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Prerequisites

- Prompt **136** (chat workspace) shipped: `frontend/src/app/(workspace)/chat/[sessionId]/page.tsx`, `ChatInputBar.tsx`, `useChat.ts`
- Prompt **116** (UI foundation) recommended for theme tokens; not blocking
- Archived STT stack: `tools/transcription_tools.py`, `config.yaml` `stt` section
- Desktop reference (read-only, do not fork): `apps/desktop/src/app/chat/composer/hooks/use-voice-recorder.ts`, `use-mic-recorder.ts`

## Product requirements

| Requirement | Detail |
| --- | --- |
| Interaction | Push-to-talk mic button beside chat input; click to start, click again to stop |
| Flow | Record in browser -> transcribe via API -> insert text into composer -> user can edit -> Send |
| Not in v1 | Always-on voice conversation, TTS auto-reply in web chat (desktop `useVoiceConversation` is out of scope) |
| Auth | Transcribe endpoint requires same session auth as other `/api/*` workspace routes |
| Privacy | Show clear "Listening..." state; no upload while idle |
| Disable path | When `stt.enabled` is false or mic permission denied, show disabled state with help text |

## Architecture decision: MUI shell + shadcn voice island

The Keprix frontend is **MUI + Emotion**, not shadcn/Tailwind today (`frontend/package.json`). Do **not** convert the whole app to shadcn.

**Approved approach:**

1. Add a **scoped Tailwind + shadcn island** only for voice UI under `frontend/src/components/ui/`
2. Wrap voice controls in a container with `className` Tailwind scope (or use `tailwindcss` with `important` selector prefix `.kp-voice` to avoid clashing with MUI)
3. Bridge into MUI `ChatInputBar` via a thin `ChatVoiceControl.tsx` wrapper

**Rejected:** Rewriting `ChatInputBar` entirely in shadcn.

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

## Files to create (this prompt: docs only)

```text
docs/features/web-voice-input.md
prompts-archive/ref-187-web-voice-architecture.md   # copy of diagram + decisions
```

Document:

- Why transcribe moves to shared router (prompt 188)
- Browser support matrix (Chrome, Firefox, Safari; HTTPS requirement for getUserMedia in production)
- `stt.enabled` and provider resolution order
- Relationship to gateway voice (Telegram etc.) and desktop Hermes

## Config surface (no new env vars for behavior)

Use existing `config.yaml`:

```yaml
stt:
  enabled: true
  provider: local   # or groq, openai, mistral, elevenlabs, xai
voice:
  max_recording_seconds: 120
```

Optional UI-only setting in workspace settings later (prompt 192): default push-to-talk vs hold-to-talk.

## Acceptance criteria (orientation prompt)

- `docs/features/web-voice-input.md` exists with architecture diagram and scope boundaries
- Team agrees: shadcn island, not full-stack migration
- Dependencies for 188-192 listed in `pending-prompts/README.md`
- No code changes required in this prompt (planning only)
