# Web voice input (chat composer)

Push-to-talk speech input for the workspace web chat. Users record in the browser, the server transcribes audio, and the transcript lands in the composer for review before Send.

## How to use the mic in chat

1. Open workspace chat at `/chat` or `/chat/[sessionId]`.
2. Click the **microphone** beside the message field (or press **Ctrl+Shift+M** while the input is focused).
3. Grant microphone permission when the browser prompts you.
4. Speak your message. A popover shows **Listening...** with a visualizer and timer.
5. Click the mic again (or **Ctrl+Shift+M**) to stop. The server transcribes the clip.
6. Review and edit the transcript in the composer, then click **Send**.

While the agent is streaming a reply, the mic is disabled. Press **Escape** while recording to cancel without transcribing.

Configure in the GUI: Settings -> Voice (`/settings/voice`). Enable/disable STT, choose provider, set max recording, and paste API keys there.

## Scope (v1)

| In scope | Out of scope (v1) |
| --- | --- |
| Push-to-talk mic beside `ChatInputBar` | Always-on voice conversation |
| Record -> transcribe -> edit -> Send | TTS auto-reply in web chat |
| Session auth on transcribe API | Hold-to-talk |
| Clear "Listening..." UI state | Wake word in browser |
| Disabled state when `stt.enabled` is false | Offline WASM whisper in browser |
| No upload while idle | Desktop `useVoiceConversation` parity |

## Backend

Shared transcription handler: `src/keprix/api/audio_transcribe.py`.

| Route | App | Auth |
| --- | --- | --- |
| `POST /api/audio/transcribe` | Main API :3333 + Hermes desktop | Required on :3333; desktop Hermes unchanged |
| `GET /api/audio/status` | Main API :3333 | Public |
| `GET /api/audio/settings` | Main API :3333 | Authenticated |
| `PUT /api/audio/settings` | Main API :3333 | Authenticated (writes config.yaml + optional env keys) |

The workspace web UI includes a mic control in `ChatInputBar.tsx`. Users can dictate into the composer, edit the transcript, then Send.

STT implementation: `src/keprix/tools/transcription_tools.py` with `stt` / `voice` in `config.yaml`.

### Rate limiting

`POST /api/audio/transcribe` is limited to **30 requests per hour per authenticated user** (community edition default via `RateLimitMiddleware`). Excess calls return **429** with `code: rate_limited`.

### UI: MUI shell + shadcn voice island

The frontend is **MUI + Emotion**, not shadcn/Tailwind globally. The approved approach:

1. Scoped Tailwind + shadcn island under `frontend/src/components/ui/`.
2. Prefix Tailwind with `.kp-voice-root` so utilities do not clash with MUI.
3. Bridge into MUI via `ChatVoiceControl.tsx`.
4. Recording and API calls in `useWebVoiceRecorder`.
5. Mic control in `ChatInputBar`.

The UI contract exposes `feature_flags.voice_input` (mirrors `stt.enabled`) so clients can hide the mic when STT is off.

### Keyboard shortcut

When the composer text field is focused, **Ctrl+Shift+M** toggles recording (start/stop). CLI `voice.record_key` is not exposed in the web UI in v1.

### Data flow

```text
[User clicks mic in ChatInputBar]
        |
        v
[useWebVoiceRecorder: MediaRecorder -> Blob webm/opus]
        |
        v
[POST /api/audio/transcribe  (main API :3333, Bearer token)]
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

### Composer layout

```text
[Attach] [Mic] [ TextField multiline ] [Send/Stop]
```

While recording, a Popover shows the `AIVoiceInput` visualizer and elapsed timer.

### Transcript merge rule

Append with a space if the composer already has text; otherwise set the field. User may edit before Send.

## Configuration

No new environment variables for behaviour. Use existing `config.yaml`:

```yaml
stt:
  enabled: true
  provider: local   # local | groq | openai | mistral | elevenlabs | xai
  local:
    model: base
    language: ""
voice:
  max_recording_seconds: 120
```

Behavioural settings stay in `config.yaml`; the workspace settings page at `/settings/voice` is read-only.

### Provider setup

| Provider | Requirement | Notes |
| --- | --- | --- |
| `local` (default) | `faster-whisper` on server | Model auto-download on first use; no API key |
| `groq` | `GROQ_API_KEY` | Fast cloud STT; see [environment variables](../configuration/environment-variables.md) |
| `openai` | `VOICE_TOOLS_OPENAI_KEY` or OpenAI audio key | Whisper-compatible API |
| `mistral` | `MISTRAL_API_KEY` | |
| `elevenlabs` | `ELEVENLABS_API_KEY` | |
| `xai` | `XAI_API_KEY` | |

If `stt.enabled` is `false`, the transcribe endpoint returns **403** and the mic control stays disabled (`GET /api/audio/status` and `feature_flags.voice_input`).

### API contract

**POST** `/api/audio/transcribe` (auth required on main API)

Request:

```json
{
  "data_url": "data:audio/webm;base64,...",
  "mime_type": "audio/webm"
}
```

Response:

```json
{
  "ok": true,
  "transcript": "user speech as text",
  "provider": "local"
}
```

**GET** `/api/audio/status`

```json
{
  "stt_enabled": true,
  "provider": "local",
  "max_recording_seconds": 120,
  "transcribe_path": "/api/audio/transcribe"
}
```

## Browser support and deployment

| Browser | `getUserMedia` | `MediaRecorder` (webm/opus) | Notes |
| --- | --- | --- | --- |
| Chrome / Edge (desktop) | Yes | Yes | Primary QA target |
| Firefox (desktop) | Yes | Yes (codec may vary) | Manual QA recommended |
| Safari (desktop) | Yes | Partial; may need fallback mime | Test on macOS |
| Mobile browsers | Yes with caveats | Variable | Not primary v1 target |

### HTTPS and reverse proxies

- `getUserMedia` requires a [secure context](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia#security): **HTTPS** in production or **localhost** in development.
- Reverse proxies must forward `POST /api/audio/transcribe` JSON bodies without stripping or re-encoding audio payloads.
- Recommended max recording length matches `voice.max_recording_seconds` in config (default 120 seconds).

## Privacy and UX

- Show explicit **Listening...** state while the mic is open.
- Do not upload audio until the user stops recording.
- Mic permission denied: disabled mic with help text (`mic-permissions.ts`).
- Mic disabled while the agent is streaming a reply (`isStreaming` on `ChatInputBar`).
- Escape while recording cancels without transcribe.
- Temp audio files on the server are deleted after transcribe.

## Difference vs desktop voice

| | Web chat (this feature) | Desktop app |
| --- | --- | --- |
| Mode | Push-to-talk dictate into composer | Dictation plus full voice conversation mode |
| TTS reply | User reads agent text; no auto TTS in v1 | Voice conversation can speak replies |
| API path | Main API :3333 with session auth | Hermes desktop bridge |
| Wake word | Not in browser v1 | Desktop wake word settings |

Desktop reference (read-only):

- `src/keprix/apps/desktop/src/app/chat/composer/hooks/use-voice-recorder.ts`
- `src/keprix/apps/desktop/src/keprix.ts` (`transcribeAudio` -> `/api/audio/transcribe`)

## Relationship to other voice surfaces

| Surface | Role |
| --- | --- |
| **Web chat (this feature)** | Push-to-talk dictate into composer; no auto TTS in v1 |
| **Messaging gateway** | Auto-transcribes voice messages on Telegram, Discord, WhatsApp, Slack, Signal |
| **CLI voice mode** | `voice.record_key`, VAD, beeps; configured under `voice.*` in config |
| **`docs/features/voice.md`** | Broader voice/STT/TTS operators guide |

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Mic icon missing or disabled | `GET /api/audio/status`; `stt.enabled` in config; `feature_flags.voice_input` in UI contract |
| Permission denied | Browser site settings; HTTPS in production |
| Empty transcript | Recording length, background noise; provider logs |
| 401 on transcribe | Logged-in session; `ce-api.ts` Bearer token |
| 413 payload too large | Shorter recording; `voice.max_recording_seconds` |
| 429 rate limited | Wait for hourly window reset; default 30 transcribes/hour per user |

## Related

- [Chat](chat.md)
- [Voice (operators)](voice.md)
- [API reference](../reference/api.md)
- [Environment variables](../configuration/environment-variables.md) (provider API keys)
- [Security architecture](../security/architecture.md) (transcribe auth and rate limits)
