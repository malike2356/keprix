# keprix - Prompt: Aiva Phone Receptionist (Twilio Voice + Agent Bridge)

## Purpose

Aiva's product promise is "hire an AI employee." The highest-value surface for that promise is the phone. A small business owner pays Aiva to answer calls, handle enquiries, book appointments, and escalate when needed.

This is not a browser voice widget. Browser voice is medium-friction -- nobody reaches for a mic when they're at a desk with a keyboard. But a phone number that Aiva answers? That replaces a real human cost. That earns its keep at Aiva's price point.

This prompt builds the phone receptionist pipeline: Twilio Voice for telephony, Deepgram or Whisper for STT, keprix's existing agent logic for responses, ElevenLabs or OpenAI TTS for voice output. The stack is model-agnostic, costs a fraction of OpenAI Realtime, and keeps the agent's brain in keprix where you control it.

## Why not OpenAI Realtime API

| Factor | OpenAI Realtime | This stack |
|---|---|---|
| Cost (10 min call) | $3.00 ($0.06/min in + $0.24/min out) | ~$0.15 (Deepgram STT + ElevenLabs TTS) |
| Model lock-in | GPT-4o only, no swap | Any STT/LLM/TTS combo |
| Agent brain | OpenAI owns the session | keprix owns the agent loop, tools, memory |
| Surface | Browser widget (wrong for Aiva) | Phone number (right for Aiva) |
| Feature customers pay for | "My AI talks" | "My AI answers my business phone" |

## What already exists (do not rebuild)

- `agent/conversation_loop.py` -- core agent logic
- `agent/system_prompt.py` -- prompt builder
- `tools/` -- 60+ tools (calendar booking, email, CRM, etc.)
- `agent/memory_manager.py` -- persistent memory across calls
- `agent/voice_mode.py` -- existing voice mode tool
- `api/audio_routes.py`, `api/audio_transcribe.py` -- existing audio endpoints
- `gateway/` -- multi-platform message routing
- `tools/tts_tool.py` -- text-to-speech
- `tools/transcription_tools.py` -- speech-to-text

## What to build

### 1. Twilio Voice Webhook Handler

A new gateway handler that receives inbound calls via Twilio:

```
src/keprix/gateway/
  twilio_voice_handler.py     - handles Twilio voice webhooks
  twilio_media_stream.py      - bidirectional audio streaming via Twilio Media Streams
```

Flow:

1. Customer calls Aiva's Twilio number.
2. Twilio sends a voice webhook to `https://core.keprix.ai/api/gateway/twilio/voice`.
3. keprix answers the call and opens a bidirectional Media Stream.
4. Audio flows: customer speech -> Twilio -> WebSocket -> keprix.
5. keprix processes: STT -> agent loop -> TTS -> WebSocket -> Twilio -> customer.

```python
# gateway/twilio_voice_handler.py

@router.post("/api/gateway/twilio/voice")
async def handle_inbound_call(request: Request):
    """Handle an inbound Twilio voice call."""
    form = await request.form()
    caller = form.get("From")
    called = form.get("To")

    # Create a voice session
    session = await voice_session_manager.create(
        caller=caller,
        called=called,
        persona="receptionist",  # Aiva receptionist persona
        business_id=resolve_business_from_number(called),
    )

    # Return TwiML to answer and start media stream
    return TwiMLResponse(
        say="Aiva speaking. How can I help?",
        stream_url=f"wss://core.keprix.ai/api/gateway/twilio/stream/{session.id}",
    )
```

### 2. Provider-Agnostic Voice Pipeline

A modular voice pipeline that can swap STT, LLM, and TTS providers:

```
src/keprix/voice/
  __init__.py
  pipeline.py                - VoicePipeline: orchestrates STT -> Agent -> TTS
  providers/
    stt/
      base.py                - abstract STT provider
      deepgram.py            - Deepgram streaming STT
      openai_whisper.py      - OpenAI Whisper
      local_whisper.py       - local Whisper (offline, no cost)
    tts/
      base.py                - abstract TTS provider
      elevenlabs.py          - ElevenLabs streaming TTS
      openai_tts.py          - OpenAI TTS
      edge_tts.py            - Microsoft Edge TTS (free, decent quality)
    llm/
      base.py                - abstract LLM provider
      keprix_agent.py        - wraps the keprix agent loop
  session.py                 - VoiceSession: tracks call state, caller context
  vad.py                     - voice activity detection, turn boundary detection
  interruptions.py           - handle barge-in (caller interrupts agent)
```

The pipeline:

```python
class VoicePipeline:
    """Orchestrates a voice call: STT -> Agent -> TTS."""

    def __init__(
        self,
        stt: STTProvider,
        agent: VoiceAgent,
        tts: TTSProvider,
    ):
        self.stt = stt
        self.agent = agent
        self.tts = tts
        self.vad = VoiceActivityDetector()
        self.interruption_handler = InterruptionHandler()

    async def run(self, audio_stream: AsyncIterator[bytes], session: VoiceSession):
        """Run the voice pipeline for the duration of the call."""
        # Load caller context from memory
        caller_context = await self.agent.load_context(session.caller)

        async for audio_chunk in audio_stream:
            # Detect if caller is speaking
            if not self.vad.is_speech(audio_chunk):
                continue

            # Transcribe speech to text
            text = await self.stt.transcribe(audio_chunk)

            if not text or len(text.strip()) < 2:
                continue  # ignore short noises

            # Check for interruption
            if self.agent.is_speaking:
                await self.interruption_handler.handle(session, text)

            # Run agent
            response = await self.agent.respond(text, session, caller_context)

            # Convert to speech
            audio = await self.tts.synthesize(response.text)

            # Stream back to caller
            yield audio

            # Save to memory
            await self.agent.save_to_memory(session, text, response)
```

### 3. Aiva Receptionist Persona

A focused agent persona for phone reception:

```python
AIVA_RECEPTIONIST_PROMPT = """
You are Aiva, the AI receptionist for {business_name}. You answer the business
phone, handle enquiries, book appointments, and take messages.

Caller context (from memory, if they have called before):
{caller_context}

Business context:
- Business: {business_name}
- Services: {business_services}
- Hours: {business_hours}
- Calendar: connected ({calendar_provider})
- Escalation: {escalation_contact} ({escalation_phone})

Voice behaviour:
- Answer within 2 seconds of the call connecting.
- Greet: "{business_greeting}, Aiva speaking. How can I help?"
- Keep responses under 20 seconds. Get to the point.
- Use active listening: "got it," "let me check that," "one moment."
- If you need to look something up, say what you're doing: "Let me pull up
  the calendar now."
- Never leave dead air. Fill gaps with context: "Still checking..."
- If the caller is angry or upset, acknowledge: "I understand this is
  frustrating. Let me get someone to help right away." Then escalate.
- Detect urgency: "urgent," "emergency," "right now" -> escalate immediately.
- Always confirm before booking: "So that's Tuesday at 2pm for a viewing.
  Is that correct?"
- End calls warmly: "Thanks for calling {business_name}. Have a great day."

Escalation triggers (transfer to human immediately):
- Caller explicitly asks for a human.
- Legal threats, complaints about service, safety/emergency.
- You cannot resolve the issue after two attempts.
- Caller is distressed or crying.

When escalating:
- Summarise the situation for the human.
- Tell the caller: "Let me connect you with {escalation_name} now."
- Transfer via Twilio <Dial>.

Tool access during calls:
- Calendar: read and create appointments
- CRM: look up contacts, add notes
- Email: send confirmations
- Memory: save call summary for next time
- NO write access to billing, settings, or any destructive tools
"""
```

### 4. Caller Memory and Context

When a call connects, the agent loads everything it knows about the caller:

```python
class CallerContext:
    """Everything the agent knows about a caller from previous interactions."""

    caller_id: str               # phone number hash
    name: str | None             # "Sarah from Flat 3"
    previous_calls: list[CallSummary]
    open_items: list[str]        # "still waiting on the boiler repair quote"
    preferences: dict            # "prefers email confirmations"
    last_call_date: datetime | None

    @classmethod
    async def from_phone(cls, phone: str) -> "CallerContext":
        """Load caller context from memory."""
        memory = await MemoryManager.search(f"caller:{phone}")
        if not memory:
            return cls(caller_id=hash(phone))
        return cls(**memory.metadata)
```

After the call, a summary is saved:

```python
class CallSummary:
    timestamp: datetime
    duration: int                # seconds
    topic: str                   # "booking a viewing for Flat 3"
    outcome: str                 # "appointment booked: Tue 2pm"
    follow_up_needed: bool
    follow_up_action: str | None # "send email confirmation"
    notes: str                   # "caller was in a hurry, spoke quickly"
```

This means the next time Sarah calls, Aiva says: "Welcome back, Sarah. Your viewing for Flat 3 is confirmed for Tuesday at 2pm. Is that what you're calling about?"

### 5. Twilio Provisioning

A setup wizard for provisioning a Twilio number:

```bash
keprix voice provision --provider twilio
```

```
Twilio Voice Setup
==================

1. Twilio credentials:
   Account SID: ACxxxxxxxxxx
   Auth Token:   [hidden]

2. Phone number:
   [Search available numbers] -> +44 20 7946 0958
   [Provision] -> Number purchased and configured.

3. Webhook configured:
   Voice webhook: https://core.keprix.ai/api/gateway/twilio/voice
   Status callback: https://core.keprix.ai/api/gateway/twilio/status

4. Test call:
   Dial +44 20 7946 0958 from your phone.
   Aiva should answer.

Done. Your Aiva phone number is +44 20 7946 0958.
Monthly cost: £1.15 (Twilio number) + usage (~£0.02/min STT + ~£0.05/min TTS).
```

### 6. Voice Session Management

Operators can monitor active calls:

```
Dashboard -> Voice

Active Calls:
+------------------+----------+---------+------------+--------+
| Caller           | Duration | Topic   | Status     | Action |
+------------------+----------+---------+------------+--------+
| +44 7700 123456  | 3:42     | Enquiry | Speaking   | [Join] |
| +44 7700 789012  | 1:15     | Booking | Processing | [Join] |
+------------------+----------+---------+------------+--------+

Today: 12 calls, 45 min total, 3 appointments booked, 1 escalated.

Call History:
[...]
```

### 7. Cost Estimation and Monitoring

Per-call cost breakdown visible in the dashboard:

```
Call #2841 | +44 7700 123456 | Duration: 5:23
  STT (Deepgram):    $0.032  (323s @ $0.0059/min)
  Agent (Claude):    $0.018  (850 input + 120 output tokens)
  TTS (ElevenLabs):  $0.081  (323s @ $0.015/min)
  Twilio:            $0.027  (5.4 min @ $0.005/min inbound)
  Total:             $0.158
```

## Files to create

```
src/keprix/gateway/
  twilio_voice_handler.py     - Twilio voice webhook handler
  twilio_media_stream.py      - bidirectional audio streaming via WebSocket

src/keprix/voice/
  __init__.py
  pipeline.py                 - VoicePipeline orchestrator
  session.py                  - VoiceSession state
  vad.py                      - voice activity detection
  interruptions.py            - barge-in handling
  caller_context.py           - CallerContext: load/save from memory
  providers/
    stt/
      base.py
      deepgram.py
      openai_whisper.py
      local_whisper.py
    tts/
      base.py
      elevenlabs.py
      openai_tts.py
      edge_tts.py
    llm/
      base.py
      keprix_agent.py         - wraps keprix agent loop for voice

src/keprix/voice/
  personas/
    receptionist.py           - Aiva receptionist persona
    meeting_assistant.py      - meeting note-taker persona
    custom.py                 - user-defined voice persona

src/keprix/voice/
  provision.py                - Twilio number provisioning wizard
  cost_tracker.py             - per-call cost estimation

src/keprix/api/
  voice_routes.py             - voice session management API
  voice_provision_routes.py   - number provisioning API

frontend/src/app/(admin)/dashboard/
  voice/
    page.tsx                  - active call monitor
    history/
      page.tsx                - call history with cost breakdown

frontend/src/app/(workspace)/settings/
  voice/
    receptionist/
      page.tsx                - receptionist persona settings
    numbers/
      page.tsx                - phone number management

docs/
  voice/aiva-phone-receptionist.md

tests/
  voice/
    test_pipeline.py
    test_vad.py
    test_interruptions.py
    test_caller_context.py
    test_twilio_handler.py
    test_personas.py
```

## Acceptance criteria

- A customer dials Aiva's Twilio number. Aiva answers within 2 seconds.
- Aiva transcribes speech, runs the agent, synthesises speech, and responds in under 2 seconds total latency.
- If the caller has called before, Aiva greets them by name and references their last interaction.
- "Book a viewing for Tuesday at 2pm" creates a calendar appointment and sends an email confirmation.
- Angry or distressed callers are escalated to the human contact. Aiva summarises the situation before transfer.
- The voice stack uses Deepgram STT + ElevenLabs TTS by default, but providers are swappable via config.
- Per-call cost is tracked and visible in the dashboard. A 5-minute call costs under $0.20.
- The operator can listen in on active calls from the dashboard.
- Silence over 10 seconds triggers a prompt: "Are you still there?"
- The receptionist persona is Aiva-branded vocabulary, not generic assistant language.
