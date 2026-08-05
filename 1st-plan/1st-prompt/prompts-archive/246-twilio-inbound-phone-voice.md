# Keprix - Prompt 245: Twilio Inbound Phone Voice Channel

## Context

Prompt 244 (Realtime Voice Agent) establishes the WebRTC/OpenAI Realtime API path for
browser and mobile voice. This prompt covers the distinct and higher-value surface:
inbound telephone calls via Twilio.

For Aiva, the phone channel is the primary business case. A small business owner's customer
rings a local number, Aiva answers, handles the enquiry, books the appointment, raises an
invoice, or escalates to a human. This replaces a part-time receptionist -- a real cost that
small businesses pay every month. It is the single feature most likely to justify Aiva's
subscription on its own.

The WebRTC approach in Prompt 244 requires OpenAI's Realtime API and locks voice to GPT-4o.
The Twilio approach here is model-agnostic: Deepgram handles STT, keprix's own agent loop
handles intelligence, ElevenLabs or OpenAI TTS handles voice out. Each layer is swappable.
Cost per minute is a fraction of GPT Realtime API pricing.

## How the call flows

```
Customer dials Twilio number assigned to this Aiva worker
  |
  v
Twilio webhook -> POST /api/voice/inbound
  | (keprix responds with TwiML: <Connect><Stream url="wss://.../voice/stream"/>)
  v
Twilio Media Stream opens WebSocket
  - sends: audio chunks (mulaw 8kHz, base64, JSON-framed)
  - receives: audio chunks back (same format) and control marks
  |
  v
keprix VoiceStreamHandler (per-call WebSocket session)
  - converts mulaw 8kHz -> PCM 16-bit
  - pipes to Deepgram streaming STT (nova-2, utterance_end detection)
  |
  v (Deepgram emits final transcript on utterance_end)
  |
  v
Aiva agent loop (same tool executor, same credential pool, same audit trail as text)
  - caller ID lookup: match Twilio From number against CRM contacts
  - greet by name if known: "Hi Sarah, it's Aiva..."
  - run tools as needed (calendar.book, crm.update, billing.check...)
  - generate text response
  |
  v
TTS (ElevenLabs or OpenAI TTS) -> mulaw 8kHz
  |
  v
streamed back to Twilio WebSocket as base64 audio marks
  |
Caller hears response (target: < 1.5s from end of utterance to first audio byte)
  |
[conversation loop until hangup or escalation trigger]
  |
  v (on call_end)
VoiceCallRecord:
  - full transcript saved
  - AI summary generated (who called, what they needed, what was done)
  - follow-up tasks created (if Aiva committed to something)
  - CRM contact updated (last called, call notes)
  - notification sent to workspace owner if escalation occurred
```

## What already exists in keprix (do not rebuild)

- `agent/tool_executor.py` -- tool execution, credential injection, guardrails
- `agent/conversation_loop.py` -- agent conversation state
- `gateway/stream_events.py` -- event routing across channels
- `gateway/twilio_voice_webhook.py` -- stub created in Prompt 244 (extend, do not replace)
- `tools/tts_tool.py` -- existing TTS tool (wire to voice output stream)
- `tools/transcription_tools.py` -- existing STT tools (voice stream replaces batch)
- `api/audio_routes.py` -- audio API base (add voice stream routes)

## What to build

### 1. Twilio webhook handler

`gateway/twilio_voice_webhook.py` (extend the stub from Prompt 244):

```python
class TwilioVoiceWebhook:
    """Handles Twilio voice call lifecycle webhooks."""

    async def handle_inbound(self, request: Request) -> TwiMLResponse:
        """POST /api/voice/inbound -- called when a call arrives."""
        # Validate Twilio signature (HMAC-SHA1 against AUTH_TOKEN)
        self._validate_signature(request)

        # Resolve which Aiva worker owns this Twilio number
        to_number = request.form.get("To")
        worker = await self.worker_registry.get_by_phone(to_number)
        if not worker:
            return TwiMLResponse().reject()

        # Log call start
        call_sid = request.form.get("CallSid")
        caller = request.form.get("From")
        await self.call_store.create(call_sid, worker_id=worker.id, caller=caller)

        # Respond with TwiML to open a Media Stream
        stream_url = f"wss://{settings.HOST}/api/voice/stream/{call_sid}"
        return TwiMLResponse().connect_stream(stream_url, call_sid=call_sid)

    async def handle_status(self, request: Request) -> None:
        """POST /api/voice/status -- called on call_end, busy, no-answer."""
        call_sid = request.form.get("CallSid")
        status = request.form.get("CallStatus")
        if status == "completed":
            await self.call_finaliser.finalise(call_sid)
```

### 2. Voice stream handler (the core)

`gateway/voice_stream_handler.py`:

```python
class VoiceStreamHandler:
    """
    Manages one phone call as a WebSocket session.

    Receives mulaw audio from Twilio, pipes to Deepgram for STT,
    feeds transcripts to the Aiva agent, gets text responses,
    converts to audio via TTS, and streams audio back to Twilio.
    """

    def __init__(self, call_sid: str, worker: AivaWorker):
        self.call_sid = call_sid
        self.worker = worker
        self.deepgram = DeepgramStreamingClient()
        self.tts = TTSStreamingClient()
        self.agent = AgentSession(worker)
        self.state = CallState.IDLE
        self.caller_context: CallerContext | None = None

    async def run(self, websocket: WebSocket):
        """Main loop: receive from Twilio, stream to Deepgram, respond."""
        await websocket.accept()

        async with self.deepgram.session() as dgram:
            # Resolve caller from CRM before first word
            self.caller_context = await self._resolve_caller()

            # Greet the caller immediately
            await self._speak(self._build_greeting(), websocket)

            async for message in websocket.iter_text():
                event = json.loads(message)

                if event["event"] == "media":
                    audio = base64.b64decode(event["media"]["payload"])
                    pcm = mulaw_to_pcm(audio)
                    await dgram.send(pcm)

                elif event["event"] == "stop":
                    break

            # Process any remaining transcript
            await dgram.finish()

        await self._finalise()

    async def _on_transcript(self, transcript: str, websocket: WebSocket):
        """Called by Deepgram on utterance_end with final transcript."""
        if self.state == CallState.SPEAKING:
            # User interrupted -- stop TTS, listen
            self.tts.interrupt()

        self.state = CallState.THINKING
        await self._log_turn("user", transcript)

        # Run agent
        response = await self.agent.respond(
            transcript,
            caller_context=self.caller_context,
            tools_allowed=self.worker.voice_tool_policy,
        )

        # Handle escalation signal
        if response.escalate:
            await self._escalate(response.escalate_to, websocket)
            return

        await self._speak(response.text, websocket)

    async def _speak(self, text: str, websocket: WebSocket):
        """Convert text to audio and stream to Twilio."""
        self.state = CallState.SPEAKING
        async for chunk in self.tts.stream(text, voice_id=self.worker.voice_id):
            mulaw_chunk = pcm_to_mulaw(chunk)
            await websocket.send_text(build_twilio_media_message(mulaw_chunk))
        self.state = CallState.LISTENING

    async def _escalate(self, escalate_to: str, websocket: WebSocket):
        """Transfer the call to a human."""
        await self._speak("Let me transfer you now.", websocket)
        await websocket.send_text(build_twilio_transfer_twiml(escalate_to))
        self.state = CallState.ESCALATED

    async def _finalise(self):
        """Post-call: summarise, update CRM, create tasks."""
        await self.call_finaliser.finalise(
            call_sid=self.call_sid,
            transcript=self.agent.transcript,
            caller_context=self.caller_context,
            agent_summary=await self.agent.summarise_call(),
        )
```

### 3. Audio conversion utilities

`gateway/voice_audio.py`:

```python
def mulaw_to_pcm(data: bytes) -> bytes:
    """Convert mulaw 8kHz to PCM 16-bit 16kHz (Deepgram prefers 16kHz)."""

def pcm_to_mulaw(data: bytes) -> bytes:
    """Convert PCM 16-bit back to mulaw 8kHz for Twilio."""

def build_twilio_media_message(audio: bytes) -> str:
    """Wrap mulaw audio in the Twilio Media Stream JSON envelope."""
    return json.dumps({
        "event": "media",
        "streamSid": "...",
        "media": {"payload": base64.b64encode(audio).decode()}
    })
```

### 4. Deepgram streaming client

`voice/deepgram_client.py`:

```python
class DeepgramStreamingClient:
    """
    Real-time STT via Deepgram nova-2.
    Emits final transcripts on utterance_end events.
    Adds < 300ms to the turn-around vs. waiting for silence detection.
    """

    async def session(self) -> AsyncContextManager:
        """Open a streaming connection to Deepgram."""
        # ws://api.deepgram.com/v1/listen?model=nova-2&utterance_end_ms=1000
        # &interim_results=true&endpointing=300

    async def send(self, pcm: bytes):
        """Send a PCM audio chunk to Deepgram."""

    async def finish(self):
        """Signal end of audio stream and await final transcript."""
```

Deepgram configuration:
- `model=nova-2` (best accuracy, lowest latency)
- `utterance_end_ms=1000` (emit utterance_end after 1 second of silence)
- `endpointing=300` (detect end of utterance in 300ms)
- `interim_results=true` (show live transcript in UI while user is talking)

### 5. TTS streaming client

`voice/tts_client.py`:

```python
class TTSStreamingClient:
    """
    Streams text-to-speech audio. Supports interruption.
    Default provider: ElevenLabs streaming API.
    Fallback: OpenAI TTS (cheaper, slightly lower quality).
    """

    async def stream(self, text: str, voice_id: str) -> AsyncIterator[bytes]:
        """Yield PCM 16-bit audio chunks as they arrive from the TTS provider."""

    def interrupt(self):
        """Cancel the current stream. Call when user interrupts agent."""
```

Provider priority:
1. ElevenLabs streaming (best naturalness, configurable voice per worker)
2. OpenAI TTS streaming (cheaper, good quality, fallback)
3. Google Cloud TTS (lowest cost, acceptable for low-tier plans)

### 6. Call state store

`voice/call_store.py`:

```python
class VoiceCallRecord:
    call_sid: str
    worker_id: str
    caller_number: str
    caller_name: str | None       # from CRM lookup
    caller_contact_id: str | None # CRM contact ID if matched
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    transcript: list[Turn]        # [{role, text, timestamp}]
    summary: str | None           # AI-generated post-call summary
    escalated: bool
    escalated_to: str | None
    tasks_created: list[str]      # task IDs created during/after call
    recording_url: str | None     # if recording enabled in settings
```

### 7. Post-call finaliser

`voice/call_finaliser.py`:

```python
class CallFinaliser:
    """Runs after every call to close the loop."""

    async def finalise(self, record: VoiceCallRecord):
        # 1. Save transcript to call store
        # 2. Generate AI summary (2-3 sentences: who, what, outcome)
        # 3. Update CRM contact (last_called, call_notes, call_count)
        # 4. Create tasks for any commitments made ("I'll send that over")
        # 5. Send post-call notification to workspace owner (configurable)
        # 6. Emit call_ended gateway event (triggers connected automations)
```

### 8. Phone number provisioning

`voice/phone_provisioning.py`:

```python
class PhoneProvisioner:
    """
    Provisions Twilio phone numbers for Aiva workers.
    Called during Aiva onboarding or from worker settings.
    """

    async def provision_for_worker(
        self,
        worker_id: str,
        country: str = "GB",
        area_code: str | None = None,
    ) -> str:
        """Buy a number from Twilio, assign to worker, configure webhook URLs."""
        number = await self.twilio.search_and_buy(country, area_code)
        await self.twilio.configure_webhooks(
            number,
            voice_url=f"https://{settings.HOST}/api/voice/inbound",
            status_url=f"https://{settings.HOST}/api/voice/status",
        )
        await self.worker_registry.assign_phone(worker_id, number)
        return number

    async def release_for_worker(self, worker_id: str):
        """Release Twilio number when worker is deleted."""
```

### 9. Escalation engine

`voice/escalation.py`:

Escalation triggers (configurable per worker):
- User explicitly asks: "can I speak to a human"
- Anger/urgency detected in transcript (keyword list + sentiment)
- Topic outside worker's configured scope
- Tool failure during critical action (e.g., booking fails)
- Call duration exceeds threshold (e.g., 15 minutes for a support worker)

Escalation actions:
- Transfer to a Twilio number (owner's mobile, another team member)
- Play a message and let the caller leave a voicemail
- Send an urgent notification to workspace owner and continue the call

### 10. Voice settings per worker

Extend `workers` table and worker settings UI:

```
Worker settings -> Voice
  Phone number: +44 7700 900123  [Release] [Buy new]
  Voice persona: [Friendly professional (default)] [Custom...]
  Voice (ElevenLabs voice ID): [Rachel] [Adam] [Custom voice...]
  Speaking pace: [Normal] [Slightly fast] [Fast]
  Tool access during calls:
    [x] Read CRM contacts
    [x] Check calendar
    [x] Book appointments
    [ ] Send emails (require confirmation)
    [ ] Update CRM (require confirmation)
    [ ] Process payments (disabled during voice)
  Escalation:
    Transfer to: [+44 7700 900456]
    Trigger keywords: [speak to human, manager, complaint, refund]
    After: [15] minutes, escalate automatically
  Post-call notifications:
    [x] Email summary to owner after every call
    [x] Slack notification if escalated
    [ ] SMS if urgent
  Call recording:
    [x] Transcript only (never store audio)
    [ ] Store audio (GDPR consent required)
```

## Files to create

```
src/keprix/gateway/
  twilio_voice_webhook.py      - extend stub from Prompt 244
  voice_stream_handler.py      - main per-call WebSocket handler
  voice_audio.py               - mulaw <-> PCM conversion, Twilio envelope builders

src/keprix/voice/
  __init__.py
  deepgram_client.py           - Deepgram nova-2 streaming STT
  tts_client.py                - ElevenLabs/OpenAI TTS streaming client
  call_store.py                - VoiceCallRecord schema and persistence
  call_finaliser.py            - post-call: summarise, CRM update, tasks, notify
  phone_provisioning.py        - Twilio number buy/release/configure
  escalation.py                - escalation triggers and actions
  caller_resolver.py           - match Twilio From number to CRM contact
  twiml_builder.py             - TwiML response helpers

src/keprix/api/
  voice_routes.py              - /api/voice/inbound, /api/voice/stream/{sid}, /api/voice/status

src/keprix/tools/
  voice_tools.py               - transfer_call, send_voicemail, get_call_transcript tools

tests/voice/
  test_voice_stream_handler.py
  test_deepgram_client.py
  test_tts_client.py
  test_call_finaliser.py
  test_phone_provisioning.py
  test_escalation.py
  test_twiml_builder.py
```

## Credentials required

```
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_API_KEY
TWILIO_API_SECRET
DEEPGRAM_API_KEY
ELEVENLABS_API_KEY        (optional; OpenAI TTS used if absent)
OPENAI_API_KEY            (TTS fallback)
```

These are injected via keprix's existing credential store. No hard-coding.

## Aiva worker persona (voice)

When a call comes in to an Aiva worker with `persona: receptionist`, the agent system
prompt is extended with:

```
You are {worker_name}, the AI receptionist for {business_name}.

Voice behaviour:
- Answer within the first sentence: "Hi, this is {worker_name} for {business_name},
  how can I help you today?"
- Keep responses under 20 seconds. Offer to email long information.
- When using a tool, narrate: "Let me check the calendar now."
- If you cannot help, say so clearly and offer to take a message or transfer.
- Use the caller's name if you know it from CRM: "Hi Sarah, good to hear from you."
- Do not read out lists. Summarise: "You have three appointments this week -- want
  me to send you the details?"

Business context: {worker_system_prompt}

CRM caller context (if matched): {caller_context}
```

## Latency targets

```
Deepgram utterance_end to first TTS audio byte:  < 800ms
First TTS audio byte to Twilio playback start:   < 200ms
Total: caller finishes speaking to hearing response: < 1.5 seconds
```

The 800ms budget for the agent loop means tool calls must either be fast
(CRM reads are < 200ms) or the agent narrates while the tool runs
("Let me check that -- one moment").

## Cost model (per minute of call)

```
Twilio inbound call:    $0.0085 / min
Deepgram nova-2 STT:    $0.0043 / min
ElevenLabs TTS:         ~$0.0150 / min (varies by plan)
LLM tokens (response):  ~$0.002  / min (GPT-4o-mini or similar)

Total:                  ~$0.03 / min

At Aiva's price point this is sustainable for moderate call volumes.
High-volume plans can substitute OpenAI TTS ($0.006/min) to bring
the total below $0.02 / min.
```

Compare: OpenAI Realtime API alone costs $0.06/min input + $0.24/min output = $0.30/min.
The Twilio + Deepgram + ElevenLabs stack is 10x cheaper for the same capability.

## Acceptance criteria

- A Twilio inbound call to a provisioned worker number is answered by Aiva.
- Caller hears a greeting within 2 seconds of the call connecting.
- Aiva correctly identifies returning callers by phone number via CRM lookup.
- Tool calls during the call (calendar check, CRM update) complete within the agent turn.
- The agent narrates while tools run so the caller never hears silence.
- User interruption stops the current agent speech and Aiva listens immediately.
- Escalation transfers the call to the configured number with a spoken handoff.
- Post-call: transcript saved, summary generated, CRM contact updated, tasks created.
- Twilio signature validation rejects unauthenticated webhook requests.
- Voice settings per worker (tools allowed, escalation trigger, voice ID) are respected.
- DEEPGRAM_API_KEY, TWILIO credentials, and ELEVENLABS_API_KEY are injected from the
  keprix credential store -- no credentials hardcoded or in environment files.
- Cost per minute of call does not exceed $0.05 at standard ElevenLabs pricing.
