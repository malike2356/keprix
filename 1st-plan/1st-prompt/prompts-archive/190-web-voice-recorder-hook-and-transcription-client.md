# Keprix - Prompt 190: Web Voice Recorder Hook and Transcription Client

## Context

Wire browser microphone capture and API transcription. Mirror desktop `use-voice-recorder.ts` behavior for the web workspace.

Depends on **188**, **189**.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/frontend/`

## Step 1: API client

Create `frontend/src/lib/audio-api.ts`:

```typescript
import { ceApi } from "@/lib/ce-api";

export type AudioStatus = {
  stt_enabled: boolean;
  provider: string | null;
  max_recording_seconds: number;
};

export type TranscribeResult = {
  ok: boolean;
  transcript: string;
  provider?: string;
};

export async function fetchAudioStatus(): Promise<AudioStatus> { ... }

export async function transcribeAudioBlob(blob: Blob): Promise<TranscribeResult> {
  const dataUrl = await blobToDataUrl(blob);
  const response = await ceApi("/api/audio/transcribe", {
    method: "POST",
    body: JSON.stringify({ data_url: dataUrl, mime_type: blob.type || "audio/webm" }),
  });
  ...
}

function blobToDataUrl(blob: Blob): Promise<string> { ... }
```

Match error handling patterns from `opportunity-api.ts` (throw with message from `detail`).

## Step 2: `useMicRecorder` (web)

Create `frontend/src/hooks/useMicRecorder.ts`:

Port logic from `apps/desktop/.../use-mic-recorder.ts` (read-only reference):

| Concern | Implementation |
| --- | --- |
| API | `navigator.mediaDevices.getUserMedia({ audio: true })` |
| Recorder | `MediaRecorder` with `mimeType` preference `audio/webm;codecs=opus`, fallback `audio/webm`, then default |
| Chunks | Collect `ondataavailable` into `Blob[]` |
| Level meter | Optional `AnalyserNode` RMS for visualizer (pass `level: number` 0-1 to UI) |
| Cleanup | Stop tracks on unmount and after stop |

Export:

```typescript
export function useMicRecorder() {
  return {
    recording: boolean,
    level: number,
    start: () => Promise<void>,
    stop: () => Promise<{ audio: Blob } | null>,
    error: string | null,
  };
}
```

## Step 3: `useWebVoiceRecorder`

Create `frontend/src/hooks/useWebVoiceRecorder.ts`:

```typescript
type UseWebVoiceRecorderOptions = {
  maxRecordingSeconds?: number;
  onTranscript: (text: string) => void;
  onError?: (message: string) => void;
  enabled?: boolean;
};

export function useWebVoiceRecorder(options: UseWebVoiceRecorderOptions) {
  // status: idle | recording | transcribing
  // elapsedSeconds: number
  // toggle: () => void
  // sttAvailable: boolean
}
```

**Behavior (match desktop):**

1. On toggle start: request mic, start MediaRecorder, start elapsed timer
2. Auto-stop at `maxRecordingSeconds` from `/api/audio/status` (default 120)
3. On toggle stop: stop recorder, POST transcribe, call `onTranscript(trimmed)`
4. Empty transcript: show warning toast (MUI `Snackbar` or existing alert pattern)
5. While `isStreaming` from chat: disable mic (parent passes `disabled`)
6. If `stt_enabled` false: `toggle` no-op + `onError` message

## Step 4: SWR status bootstrap

In hook or `ChatInputBar` parent:

```typescript
const { data: audioStatus } = useSWR("audio-status", fetchAudioStatus);
```

Revalidate on focus.

## Step 5: Browser permission UX

Create `frontend/src/lib/mic-permissions.ts`:

- `checkMicrophonePermission(): Promise<PermissionState | "unsupported">`
- Map `NotAllowedError` to user string: "Microphone blocked. Allow mic access in browser settings."

## Tests

`frontend/src/hooks/useWebVoiceRecorder.test.ts`:

- Mock `useMicRecorder`, `transcribeAudioBlob`
- toggle start -> recording status
- stop with mock transcript -> `onTranscript` called
- transcribe failure -> `onError`

`frontend/src/lib/audio-api.test.ts`:

- Mock `ceApi` response parsing

## Acceptance criteria

- Hook compiles and exports stable API used by `ChatInputBar`
- Transcribe calls `/api/audio/transcribe` on port 3333 with auth header
- No `window.hermesDesktop` usage (web only)
- Tests pass: `cd frontend && pnpm test`
