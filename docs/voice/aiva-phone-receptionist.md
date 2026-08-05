# Aiva phone receptionist

Aiva phone receptionist answers inbound Twilio calls, streams caller audio through Keprix, runs a provider-agnostic STT -> agent -> TTS pipeline, and returns speech to the caller.

Core routes:

- `POST /api/gateway/twilio/voice`
- `WS /api/gateway/twilio/stream/{session_id}`
- `POST /api/gateway/twilio/status`
- `POST /api/voice/inbound`
- `WS /api/voice/stream/{call_sid}`
- `POST /api/voice/status`
- `GET /api/voice/phone/sessions`
- `POST /api/voice/phone/provision/twilio`

The default stack is Deepgram-style STT, Keprix voice agent, and ElevenLabs-style TTS. Providers are replaceable through the interfaces under `keprix.voice.providers`.

The Aiva receptionist persona is concise, confirms bookings before creating them, and escalates emergencies, legal threats, distressed callers, or explicit human requests.

The inbound phone channel validates Twilio signatures when `TWILIO_AUTH_TOKEN` is available, creates a per-call record keyed by `CallSid`, streams Twilio media envelopes through the phone handler, and finalises every call with transcript turns, a short summary, escalation state, and follow-up task placeholders.

Audio helpers convert Twilio mulaw 8 kHz payloads to PCM for STT and back to mulaw for playback. The streaming client facades default to Deepgram-style STT and ElevenLabs-style TTS while keeping credentials outside code and ready for injection through Keprix credential management.
