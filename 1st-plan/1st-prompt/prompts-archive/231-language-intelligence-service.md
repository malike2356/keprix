# keprix ML: Language Intelligence Service (Prompt 231)

**Series:** ML infrastructure (229-232). Builds on scaffold from 229 and can run in parallel with 230.
**Platform:** keprix agent OS kernel
**Phase:** Phase 2 (build now; activate at WhatsApp agent launch)
**Principle:** All language conversion (speech, translation, detection, synthesis) is a keprix tool. WhatsApp audio messages enter as bytes and exit as understood text before any agent logic runs.

---

## 1. What this prompt builds

- Language detection: fastText model, `detect_language` tool
- Translation: NLLB-200 distilled (self-hosted Docker) with auto-detection, `translate` tool
- Speech-to-text: Whisper medium (self-hosted) with Whisper API fallback, `transcribe_audio` tool
- Text-to-speech: ElevenLabs API, `synthesize_speech` tool
- WhatsApp audio handling pipeline: OGG Opus in, transcribed text out
- Provider implementations for all four stubs left empty in 229

---

## 2. Supported languages (priority)

| Code | Language | Notes |
|---|---|---|
| en | English | Primary; all models |
| tw | Twi (Akan) | NLLB code: `twi_Latn`; fastText detects as `tw` |
| ee | Ewe | NLLB code: `ewe_Latn` |
| gaa | Ga | NLLB code: `gaa_Latn` |
| ha | Hausa | NLLB code: `hau_Latn` |
| dag | Dagbani | NLLB code: `daa_Latn` |
| fr | French | Border regions; NLLB supports |

NLLB language code mapping must be stored in `providers/nllb_provider.py` as a dict, not hard-coded in service logic.

---

## 3. Self-hosted model infrastructure

### 3.1 NLLB Docker service

Add to docker-compose.yml:

```yaml
  nllb-service:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./apps/ml-service/models/nllb:/models
      - ./apps/ml-service/nllb_server:/app
    command: uvicorn server:app --host 0.0.0.0 --port 8210
    ports:
      - "8210:8210"
    environment:
      MODEL_PATH: /models/nllb-200-distilled-600M
    deploy:
      resources:
        limits:
          memory: 4G
```

Create `apps/ml-service/nllb_server/server.py`:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
import os

app = FastAPI()
MODEL_PATH = os.environ.get("MODEL_PATH", "facebook/nllb-200-distilled-600M")

print("Loading NLLB model...")
_tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
_model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)
print("NLLB ready.")

class TranslateRequest(BaseModel):
    text: str
    src_lang: str
    tgt_lang: str
    max_new_tokens: int = 400

@app.post("/translate")
def translate(req: TranslateRequest):
    pipe = pipeline(
        "translation",
        model=_model,
        tokenizer=_tokenizer,
        src_lang=req.src_lang,
        tgt_lang=req.tgt_lang,
        max_length=req.max_new_tokens,
    )
    result = pipe(req.text)
    return {"translated_text": result[0]["translation_text"]}

@app.get("/health")
def health():
    return {"status": "ok"}
```

Model download command (run once before first start):

```bash
python -c "
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
path = 'apps/ml-service/models/nllb/nllb-200-distilled-600M'
AutoTokenizer.from_pretrained('facebook/nllb-200-distilled-600M').save_pretrained(path)
AutoModelForSeq2SeqLM.from_pretrained('facebook/nllb-200-distilled-600M').save_pretrained(path)
print('Saved to', path)
"
```

### 3.2 Whisper self-hosted (local runner)

The faster-whisper library runs in-process in the ml-service (not a separate Docker service). It loads lazily on first transcription request to avoid startup delay.

```python
# In providers/whisper_provider.py
from faster_whisper import WhisperModel
from .base import STTProvider
import io

class WhisperLocalProvider(STTProvider):
    def __init__(self, model_path: str = "medium"):
        self._model: WhisperModel | None = None
        self._model_path = model_path

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(self._model_path, device="cpu", compute_type="int8")
        return self._model

    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._transcribe_sync, audio_bytes, language)

    def _transcribe_sync(self, audio_bytes: bytes, language: str | None) -> str:
        model = self._get_model()
        audio_file = io.BytesIO(audio_bytes)
        segments, info = model.transcribe(
            audio_file,
            language=language if language and language != "auto" else None,
            beam_size=5,
        )
        return " ".join(seg.text for seg in segments).strip()
```

---

## 4. Provider implementations (fill in stubs from 229)

### 4.1 providers/nllb_provider.py

```python
import httpx
from .base import TranslationProvider

# BCP-47 -> NLLB internal code
NLLB_LANG_MAP: dict[str, str] = {
    "en": "eng_Latn",
    "tw": "twi_Latn",
    "ee": "ewe_Latn",
    "gaa": "gaa_Latn",
    "ha": "hau_Latn",
    "dag": "daa_Latn",
    "fr": "fra_Latn",
    "pt": "por_Latn",
    "ar": "arb_Arab",
}

class NLLBProvider(TranslationProvider):
    def __init__(self, service_url: str = "http://nllb-service:8210"):
        self.url = service_url

    def _to_nllb(self, lang: str) -> str:
        code = NLLB_LANG_MAP.get(lang)
        if not code:
            raise ValueError(f"Unsupported language for NLLB: {lang}")
        return code

    async def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self.url}/translate", json={
                "text": text,
                "src_lang": self._to_nllb(src_lang),
                "tgt_lang": self._to_nllb(tgt_lang),
            })
            resp.raise_for_status()
            return resp.json()["translated_text"]
```

### 4.2 providers/elevenlabs_provider.py

```python
import httpx
from .base import TTSProvider

ELEVENLABS_DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # Rachel - neutral English

class ElevenLabsProvider(TTSProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def synthesize(self, text: str, voice_id: str = ELEVENLABS_DEFAULT_VOICE) -> bytes:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.content  # MP3 bytes
```

---

## 5. Language service (services/language_service.py)

```python
import base64
import hashlib
from langdetect import detect, detect_langs, LangDetectException

from ..providers.base import STTProvider, TTSProvider, TranslationProvider
from ..utils.caching import get_cached, set_cached
from ..utils.errors import UnsupportedLanguageError

SUPPORTED_AUDIO_TYPES = {"audio/ogg", "audio/mp3", "audio/wav", "audio/mpeg", "audio/webm"}

class LanguageService:
    def __init__(
        self,
        stt: STTProvider,
        tts: TTSProvider,
        translator: TranslationProvider,
    ):
        self.stt = stt
        self.tts = tts
        self.translator = translator

    # --- Language detection ---

    def detect_language(self, text: str) -> dict:
        if len(text.strip()) < 10:
            return {"language": "en", "confidence": 0.5, "script": "Latn"}
        try:
            langs = detect_langs(text)
            top = langs[0]
            return {
                "language": top.lang,
                "confidence": round(top.prob, 3),
                "script": "Latn",  # fastText gives script; langdetect does not
            }
        except LangDetectException:
            return {"language": "en", "confidence": 0.0, "script": "Latn"}

    # --- Translation ---

    async def translate(self, text: str, src_lang: str, tgt_lang: str) -> dict:
        if src_lang == "auto":
            detected = self.detect_language(text)
            src_lang = detected["language"]

        if src_lang == tgt_lang:
            return {"translated_text": text, "src_lang": src_lang}

        cache_payload = {"text": text, "src": src_lang, "tgt": tgt_lang}
        cached = await get_cached("translate", cache_payload)
        if cached:
            return cached

        translated = await self.translator.translate(text, src_lang, tgt_lang)
        result = {"translated_text": translated, "src_lang": src_lang}
        await set_cached("translate", cache_payload, result, ttl=3600)
        return result

    # --- Speech to text ---

    async def transcribe(self, audio_b64: str, mime_type: str, language: str | None = None) -> dict:
        if mime_type not in SUPPORTED_AUDIO_TYPES:
            raise UnsupportedLanguageError(f"Unsupported mime type: {mime_type}")

        audio_bytes = base64.b64decode(audio_b64)
        lang_hint = None if language == "auto" else language

        transcript = await self.stt.transcribe(audio_bytes, lang_hint)

        detected_lang = None
        if language == "auto" and transcript:
            detected_lang = self.detect_language(transcript).get("language")

        return {
            "text": transcript.strip(),
            "detected_language": detected_lang,
        }

    # --- Text to speech ---

    async def synthesize(self, text: str, voice_id: str = "") -> dict:
        audio_bytes = await self.tts.synthesize(text, voice_id or "default")
        return {
            "audio_b64": base64.b64encode(audio_bytes).decode("utf-8"),
            "mime_type": "audio/mpeg",
        }
```

---

## 6. Language router (routers/language.py)

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services.language_service import LanguageService
from ..dependencies import get_language_service

router = APIRouter()

class DetectRequest(BaseModel):
    text: str

class TranslateRequest(BaseModel):
    text: str
    src_lang: str = "auto"
    tgt_lang: str

class TranscribeRequest(BaseModel):
    audio_b64: str
    mime_type: str
    language: str = "auto"

class SynthesizeRequest(BaseModel):
    text: str
    language: str = "en"
    voice_id: str = ""

@router.post("/detect")
async def detect_language(req: DetectRequest, svc: LanguageService = Depends(get_language_service)):
    return svc.detect_language(req.text)

@router.post("/translate")
async def translate(req: TranslateRequest, svc: LanguageService = Depends(get_language_service)):
    return await svc.translate(req.text, req.src_lang, req.tgt_lang)

@router.post("/transcribe")
async def transcribe(req: TranscribeRequest, svc: LanguageService = Depends(get_language_service)):
    return await svc.transcribe(req.audio_b64, req.mime_type, req.language)

@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest, svc: LanguageService = Depends(get_language_service)):
    return await svc.synthesize(req.text, req.voice_id)
```

---

## 7. TypeScript client (packages/ml-client/src/language-client.ts)

```typescript
import { MLServiceClient } from "./index"
import type {
  DetectLanguageRequest,
  DetectLanguageResponse,
  TranslateRequest,
  TranslateResponse,
  TranscribeRequest,
  TranscribeResponse,
} from "./types"

export interface SynthesizeRequest {
  text: string
  language?: string
  voice_id?: string
}

export interface SynthesizeResponse {
  audio_b64: string
  mime_type: string
}

export class LanguageClient extends MLServiceClient {
  async detectLanguage(req: DetectLanguageRequest): Promise<DetectLanguageResponse> {
    return this.post("/language/detect", req)
  }

  async translate(req: TranslateRequest): Promise<TranslateResponse> {
    return this.post("/language/translate", req)
  }

  async transcribe(req: TranscribeRequest): Promise<TranscribeResponse> {
    return this.post("/language/transcribe", req)
  }

  async synthesize(req: SynthesizeRequest): Promise<SynthesizeResponse> {
    return this.post("/language/synthesize", req)
  }
}
```

---

## 8. WhatsApp audio pipeline

This is the full pipeline for handling a WhatsApp voice message before any agent logic runs:

```typescript
// In the WhatsApp message handler (where WhatsApp webhook events arrive)
import { LanguageClient } from "@keprix/ml-client"

const language = new LanguageClient()

async function handleWhatsAppAudioMessage(event: WhatsAppAudioEvent): Promise<string> {
  // 1. Download audio from WhatsApp media URL
  const audioBuffer = await downloadWhatsAppMedia(event.media_id)
  const audioB64 = audioBuffer.toString("base64")

  // 2. Transcribe (Whisper handles OGG Opus natively)
  const transcription = await language.transcribe({
    audio_b64: audioB64,
    mime_type: "audio/ogg",  // WhatsApp voice notes are OGG Opus
    language: "auto",
  })

  // 3. Translate to English if needed (all agent logic runs in English)
  let textForAgent = transcription.text
  const detectedLang = transcription.detected_language ?? "en"

  if (detectedLang !== "en") {
    const translation = await language.translate({
      text: transcription.text,
      src_lang: detectedLang,
      tgt_lang: "en",
    })
    textForAgent = translation.translated_text
  }

  // 4. Attach metadata so the agent knows the original language
  return JSON.stringify({
    text: textForAgent,
    original_language: detectedLang,
    original_text: transcription.text,
    input_type: "voice_message",
  })
}

async function sendWhatsAppVoiceReply(memberId: string, text: string, lang: string): Promise<void> {
  // If member's preferred language is not English, translate back
  let replyText = text
  if (lang !== "en") {
    const translated = await language.translate({ text, src_lang: "en", tgt_lang: lang })
    replyText = translated.translated_text
  }

  // Synthesize to audio
  const audio = await language.synthesize({ text: replyText, language: lang })
  await sendWhatsAppAudioMessage(memberId, audio.audio_b64)
}
```

---

## 9. keprix tool implementations

Replace stubs from 229:

```typescript
{
  name: "detect_language",
  handler: async (args: { text: string }) => {
    return languageClient.detectLanguage({ text: args.text })
  },
},
{
  name: "translate",
  handler: async (args: { text: string; src_lang: string; tgt_lang: string }) => {
    return languageClient.translate(args)
  },
},
{
  name: "transcribe_audio",
  handler: async (args: { audio_b64: string; mime_type: string; language?: string }) => {
    return languageClient.transcribe({
      audio_b64: args.audio_b64,
      mime_type: args.mime_type,
      language: args.language ?? "auto",
    })
  },
},
{
  name: "synthesize_speech",
  handler: async (args: { text: string; language?: string; voice_id?: string }) => {
    return languageClient.synthesize({
      text: args.text,
      language: args.language ?? "en",
      voice_id: args.voice_id ?? "",
    })
  },
},
```

---

## 10. Wiring in main.py (additions to 229 lifespan)

```python
from .providers.nllb_provider import NLLBProvider
from .providers.whisper_provider import WhisperLocalProvider
from .providers.openai_provider import OpenAISTTProvider
from .providers.elevenlabs_provider import ElevenLabsProvider
from .services.language_service import LanguageService

_language_svc: LanguageService | None = None

# In lifespan, after db pool init:
if settings.primary_stt_provider == "local":
    stt_provider = WhisperLocalProvider(settings.whisper_model_path)
else:
    stt_provider = OpenAISTTProvider(settings.openai_api_key)

tts_provider = ElevenLabsProvider(settings.elevenlabs_api_key) if settings.elevenlabs_api_key else None
translation_provider = NLLBProvider()  # connects to nllb-service Docker

_language_svc = LanguageService(
    stt=stt_provider,
    tts=tts_provider,
    translator=translation_provider,
)

async def get_language_service() -> LanguageService:
    return _language_svc
```

---

## 11. Health check additions

Add to `routers/health.py`:

```python
# Check NLLB service
try:
    async with httpx.AsyncClient(timeout=3) as c:
        await c.get("http://nllb-service:8210/health")
    providers["nllb"] = "ok"
except Exception:
    providers["nllb"] = "unavailable"

# Check ElevenLabs (just ping the API)
if settings.elevenlabs_api_key:
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": settings.elevenlabs_api_key})
            providers["elevenlabs"] = "ok" if r.status_code == 200 else "degraded"
    except Exception:
        providers["elevenlabs"] = "unavailable"
```

---

## 12. Acceptance criteria

1. `POST /language/detect` with `"Mepa wo kyew"` (Twi for "please") returns `{ "language": "tw", ... }`
2. `POST /language/translate` with `{ "text": "Hello", "src_lang": "en", "tgt_lang": "tw" }` returns a Twi sentence (verify with native speaker or reference translation)
3. `POST /language/translate` with `{ "src_lang": "auto", ... }` detects source language and translates correctly
4. `POST /language/transcribe` with a test OGG audio file (English) returns accurate transcript
5. `POST /language/synthesize` returns non-empty `audio_b64` and `mime_type: "audio/mpeg"`
6. NLLB Docker service starts and responds to `/health` within 60 seconds of `docker compose up`
7. Whisper local model loads lazily on first `/language/transcribe` call; subsequent calls reuse the loaded model
8. WhatsApp audio pipeline: given a base64-encoded OGG voice note in Twi, the handler returns English text with `original_language: "tw"`
9. `detect_language` tool returns structured JSON; `transcribe_audio` tool returns `{ text, detected_language }` shape
10. Translation results cached in Redis; repeated identical request returns within 5ms

---

## 13. Cost control notes

- fastText language detection is free and local; use it to gate translation (skip if already English)
- Whisper self-hosted has zero per-call cost; use for all voice messages
- ElevenLabs is billed per character; only invoke `synthesize_speech` when voice reply is explicitly requested by the agent, not by default
- NLLB self-hosted has zero per-call cost after initial model download (~2.4 GB)
- Cache all translation results for 1 hour to absorb repeated phrases (common in member queries)

---

## 14. Fallback chain

| Capability | Primary | Fallback |
|---|---|---|
| STT | Whisper local | OpenAI Whisper API |
| Translation | NLLB self-hosted | (none; if NLLB is down, return original text with error note) |
| Language detection | langdetect library | fallback to "en" with 0.0 confidence |
| TTS | ElevenLabs API | (none; if TTS unavailable, skip audio reply, send text only) |

Implement fallback chain in the service layer, not in the route handler.
