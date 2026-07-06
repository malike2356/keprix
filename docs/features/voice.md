# Voice

Voice enables speech-to-text input and text-to-speech output in the Keprix web UI and messaging channels. Talk to the agent and hear its responses spoken back.

## Enabling voice

```bash
KEPRIX_VOICE_ENABLED=true
```

Voice requires at least one STT (speech-to-text) and one TTS (text-to-speech) provider to be configured.

## STT providers

### Whisper (local)

Runs OpenAI Whisper models locally via the `whisper` Docker sidecar. No data leaves your instance.

```bash
KEPRIX_STT_PROVIDER=whisper
KEPRIX_WHISPER_MODEL=base.en    # tiny.en, base.en, small.en, medium.en, large-v3
KEPRIX_WHISPER_DEVICE=cpu       # or: cuda (if GPU available)
```

Larger models are more accurate but slower. `base.en` is a good default for English.

### OpenAI Whisper API

Send audio to the OpenAI transcription API:

```bash
KEPRIX_STT_PROVIDER=openai_whisper
OPENAI_API_KEY=sk-...
KEPRIX_WHISPER_API_MODEL=whisper-1
```

### Azure Speech

```bash
KEPRIX_STT_PROVIDER=azure_speech
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastus
```

### Web Speech API (browser-only)

Uses the browser's built-in Web Speech API. No server-side STT configuration needed; the browser sends no audio to Keprix. Availability depends on the browser and OS.

```bash
KEPRIX_STT_PROVIDER=web_speech_api
```

## TTS providers

### piper (local)

Runs the Piper TTS engine locally via the `piper` Docker sidecar. Fast, no external API needed.

```bash
KEPRIX_TTS_PROVIDER=piper
KEPRIX_PIPER_VOICE=en_US-lessac-medium   # see Piper voice list
```

Download additional voices:

```bash
python3 -m keprix.keprix_cli.main voice download-voice en_GB-jenny-medium
```

### OpenAI TTS

```bash
KEPRIX_TTS_PROVIDER=openai_tts
OPENAI_API_KEY=sk-...
KEPRIX_OPENAI_TTS_VOICE=nova    # alloy, echo, fable, onyx, nova, shimmer
KEPRIX_OPENAI_TTS_MODEL=tts-1
```

### ElevenLabs

```bash
KEPRIX_TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=...
KEPRIX_ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

### Azure Speech TTS

```bash
KEPRIX_TTS_PROVIDER=azure_speech
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastus
KEPRIX_AZURE_TTS_VOICE=en-US-JennyNeural
```

## Using voice in the web UI

When voice is enabled, a microphone icon appears in the chat input bar.

- **Click** to start recording. Recording stops when you click again or after `KEPRIX_VOICE_VAD_SILENCE_MS` milliseconds of silence (default: 800ms).
- The audio is transcribed and inserted into the text box. Press Enter to send or edit first.
- Responses are spoken automatically if **Auto-play TTS** is enabled in user settings (**Profile > Voice**).
- Click the speaker icon on any message to play or replay it.

## Voice activity detection

```bash
KEPRIX_VOICE_VAD_ENABLED=true
KEPRIX_VOICE_VAD_SILENCE_MS=800     # silence threshold to end recording
KEPRIX_VOICE_VAD_MODEL=silero       # or: webrtc, none
```

VAD prevents sending empty audio or background noise. `silero` is the highest-quality option; `webrtc` is faster.

## Voice in Telegram and Discord

When voice is enabled and a bot is configured, the agent can:

- Transcribe voice messages sent by users in Telegram or Discord.
- Reply with a voice message (TTS) if the channel is configured with `voice_reply: true`.

Configure per-channel in **Settings > Messaging > {channel} > Voice**.

## Language and locale

Set the default language for STT:

```bash
KEPRIX_VOICE_LANGUAGE=en    # ISO 639-1 code; Whisper auto-detects if omitted
```

TTS voice language is determined by the voice selected; pick a voice that matches your users' locale.

## Related

- [Messaging channels](messaging.md)
- [Localization](localization.md)
- [Environment variables](../configuration/environment-variables.md)
