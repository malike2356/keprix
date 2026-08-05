# Keprix - Prompt 191: Chat Composer Voice Integration (Web UI)

## Context

Add the mic control to the workspace chat input so users can dictate into the agent. This is the user-visible feature.

Depends on **189**, **190**, **136** (chat pages).

## Working directory

`/opt/lampp/htdocs/verlox/keprix/frontend/`

## Primary integration point

Edit `frontend/src/components/workspace/ChatInputBar.tsx`.

### Current layout

```text
[Attach] [ TextField multiline ] [Send/Stop]
```

### Target layout

```text
[Attach] [Mic] [ TextField multiline ] [Send/Stop]
```

## Implementation

### 1. Props extension

```typescript
type ChatInputBarProps = {
  onSend: (text: string, fileIds: string[]) => Promise<void> | void;
  onStop: () => void;
  isStreaming?: boolean;
};
```

No new props required if hook lives inside `ChatInputBar`.

### 2. Voice hook wiring

Inside `ChatInputBar`:

```typescript
const [voiceError, setVoiceError] = React.useState<string | null>(null);

const { toggle, status, elapsedSeconds, level, sttAvailable } = useWebVoiceRecorder({
  enabled: !isStreaming,
  onTranscript: (text) => {
    setValue((prev) => (prev.trim() ? `${prev.trim()} ${text}` : text));
    inputRef.current?.focus();
  },
  onError: (msg) => setVoiceError(msg),
});
```

**Transcript merge rule:** Append with space if field non-empty; else set. User edits before Send.

### 3. UI choice

**Option A (recommended):** Compact mic `IconButton` (MUI) for toolbar consistency, with `ChatVoiceControl` / visualizer in a `Popover` while recording.

**Option B:** Inline `AIVoiceInput` below textarea (more vertical space).

Implement **Option A** for production; keep `AIVoiceInput` in Popover content for visualizer + timer.

Mic button states:

| State | Icon | Color |
| --- | --- | --- |
| idle | `MicIcon` | default |
| recording | `MicIcon` + pulse | `error` or `primary` |
| transcribing | `CircularProgress` size 20 | disabled |
| disabled (no STT / streaming) | `MicOffIcon` | disabled |

### 4. Keyboard shortcut (optional)

`Ctrl+Shift+M` toggles recording when input focused. Document in `docs/features/web-voice-input.md`. Match CLI `voice.record_key` only if config exposed; otherwise hardcode and note future settings prompt.

### 5. Escape cancels recording

If `event.key === "Escape"` while recording, stop without transcribe (discard audio).

### 6. Chat session page

`frontend/src/app/(workspace)/chat/[sessionId]/page.tsx`: no change required if `ChatInputBar` encapsulates voice.

Also wire on `frontend/src/app/(workspace)/chat/page.tsx` if it uses the same bar for new sessions.

### 7. Empty state hint

`ChatEmptyState.tsx`: add optional line under starters: "Or click the microphone to speak your message."

## Accessibility

- Mic button `aria-label`: "Start voice input" / "Stop recording" / "Transcribing"
- `aria-pressed` while recording
- Live region: `aria-live="polite"` for "Listening..." and errors

## Error display

Show `voiceError` as `Alert` severity="warning" above input (same row as file chips), dismissible.

## Tests

`frontend/src/components/workspace/ChatInputBar.test.tsx`:

- Renders mic button when `stt_enabled` mock true
- Mic disabled when `isStreaming`
- Mock hook `onTranscript` updates textarea value
- Send still works after voice fill

`tests/frontend/test_voice_chat_surface.py` (pytest, file guard):

- `ChatInputBar.tsx` imports `useWebVoiceRecorder`
- `audio-api.ts` exists

## Acceptance criteria

- User can record, transcribe, edit, and send a message on `/chat/[sessionId]`
- Mic disabled during agent streaming
- No regression to attach/send/Enter-to-send behavior
- Visualizer visible while recording (Popover or inline)
- Frontend tests pass

## Manual test script

1. Log in at `localhost:3000`, open chat
2. Grant mic permission
3. Click mic, speak "What is DCB0129", stop
4. Text appears in input; click Send
5. Agent responds
6. Deny mic in browser; confirm clear error
