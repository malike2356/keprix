# keprix ML Service: Architecture and Scaffold (Prompt 229)

**Series:** ML infrastructure for keprix (229-232). Build all four in order. Do not start 230-232 before this scaffold is verified.
**Platform:** keprix agent OS kernel
**Principle:** All ML capabilities are keprix tools. No application code calls ML APIs directly. Every capability is registered in the keprix tool registry and invoked by agents through the standard tool call interface.

---

## 1. What this prompt builds

A standalone `ml-service` Python application within the keprix monorepo that:
- Exposes a FastAPI HTTP server consumed by the keprix TypeScript core via an internal client
- Houses all four ML capability groups (inference, embeddings, language, classifiers) as separate routers
- Provides a unified provider adapter layer so the keprix core never imports a vendor SDK directly
- Registers all ML tools in the keprix tool registry so agents can call them by name

This prompt covers: directory structure, provider adapters, shared utilities, health checks, service wiring, and the TypeScript client package. It does NOT implement the capability logic; that is in prompts 230-232.

---

## 2. Directory layout

Create the following inside the keprix monorepo:

```
keprix/
  apps/
    ml-service/
      pyproject.toml          # package metadata + dependencies
      Dockerfile
      .env.example
      main.py                 # FastAPI app, router registration, lifespan
      config.py               # settings via pydantic-settings
      routers/
        __init__.py
        health.py
        embeddings.py         # prompt 230
        language.py           # prompt 231
        classifiers.py        # prompt 232
      providers/
        __init__.py
        base.py               # abstract base classes for each provider type
        anthropic_provider.py # Claude inference adapter
        voyage_provider.py    # Voyage AI embeddings
        openai_provider.py    # OpenAI embeddings fallback + Whisper API
        groq_provider.py      # Groq fast inference fallback
        nllb_provider.py      # NLLB self-hosted translation (prompt 231)
        whisper_provider.py   # Whisper self-hosted STT (prompt 231)
        elevenlabs_provider.py # ElevenLabs TTS (prompt 231)
      services/
        __init__.py
        embedding_service.py  # implemented in prompt 230
        language_service.py   # implemented in prompt 231
        classifier_service.py # implemented in prompt 232
      utils/
        __init__.py
        chunking.py           # document chunking strategies
        caching.py            # Redis cache layer for embeddings
        logging.py            # structured JSON logging
        errors.py             # shared exception types

  packages/
    ml-client/               # TypeScript internal client
      package.json
      tsconfig.json
      src/
        index.ts             # re-exports all clients
        types.ts             # shared request/response types
        embedding-client.ts
        language-client.ts
        classifier-client.ts
        health-client.ts
      __tests__/
        embedding-client.test.ts
```

---

## 3. Python service setup

### 3.1 pyproject.toml dependencies

```toml
[project]
name = "keprix-ml-service"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "httpx>=0.27",
  "anthropic>=0.34",
  "voyageai>=0.3",
  "openai>=1.35",
  "groq>=0.9",
  "redis[hiredis]>=5.0",
  "structlog>=24",
  "tenacity>=8.3",     # retry logic for provider calls
  "tiktoken>=0.7",     # token counting for chunking
  "langdetect>=1.0.9", # language detection library
  "fasttext-langdetect>=1.0.5",  # optional faster alternative
]

[project.optional-dependencies]
local = [
  # for self-hosted models (prompt 231 and 232)
  "torch>=2.3",
  "transformers>=4.43",
  "faster-whisper>=1.0",
  "scikit-learn>=1.5",
  "joblib>=1.4",
  "numpy>=1.26",
]
```

### 3.2 config.py

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="KEPRIX_ML_")

    # Service
    host: str = "0.0.0.0"
    port: int = 8200
    log_level: str = "INFO"
    environment: Literal["development", "production"] = "development"

    # Provider keys
    anthropic_api_key: str
    voyage_api_key: str
    openai_api_key: str = ""         # optional fallback
    groq_api_key: str = ""           # optional speed fallback
    elevenlabs_api_key: str = ""     # optional TTS

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    embedding_cache_ttl_seconds: int = 86400  # 24h

    # Inference preferences
    primary_llm_provider: Literal["anthropic", "openai", "groq"] = "anthropic"
    primary_embedding_provider: Literal["voyage", "openai"] = "voyage"
    primary_stt_provider: Literal["openai", "local"] = "openai"
    primary_tts_provider: Literal["elevenlabs", "local"] = "elevenlabs"
    primary_translation_provider: Literal["nllb", "google"] = "nllb"

    # Local model paths (used in prompts 231 and 232)
    whisper_model_path: str = "models/whisper-medium"
    nllb_model_path: str = "models/nllb-200-distilled-600M"
    classifier_model_dir: str = "models/classifiers"

    # Database (for vector store - prompt 230)
    database_url: str = "postgresql://localhost:5432/keprix"

settings = Settings()
```

### 3.3 main.py

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .routers import health, embeddings, language, classifiers
from .utils.logging import configure_logging
from .utils.caching import init_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_cache()
    yield

app = FastAPI(
    title="keprix ML Service",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "development" else None,
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(embeddings.router, prefix="/embeddings", tags=["embeddings"])
app.include_router(language.router, prefix="/language", tags=["language"])
app.include_router(classifiers.router, prefix="/classifiers", tags=["classifiers"])
```

### 3.4 providers/base.py (abstract interfaces)

```python
from abc import ABC, abstractmethod
from typing import Any

class InferenceProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], model: str, **kwargs) -> str: ...

class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str], model: str) -> list[list[float]]: ...
    @abstractmethod
    def dimensions(self, model: str) -> int: ...

class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, language: str | None) -> str: ...

class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice_id: str) -> bytes: ...

class TranslationProvider(ABC):
    @abstractmethod
    async def translate(self, text: str, src_lang: str, tgt_lang: str) -> str: ...
```

---

## 4. Provider adapters (implement all stubs; logic added in 230-232)

### 4.1 voyage_provider.py

```python
import voyageai
from .base import EmbeddingProvider

VOYAGE_DIMENSIONS = {
    "voyage-3": 1024,
    "voyage-3-lite": 512,
    "voyage-code-3": 1024,
}

class VoyageProvider(EmbeddingProvider):
    def __init__(self, api_key: str):
        self.client = voyageai.AsyncClient(api_key=api_key)

    async def embed(self, texts: list[str], model: str = "voyage-3") -> list[list[float]]:
        result = await self.client.embed(texts, model=model, input_type="document")
        return result.embeddings

    def dimensions(self, model: str = "voyage-3") -> int:
        return VOYAGE_DIMENSIONS.get(model, 1024)
```

### 4.2 anthropic_provider.py

```python
import anthropic
from .base import InferenceProvider

class AnthropicProvider(InferenceProvider):
    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(self, messages: list[dict], model: str = "claude-sonnet-4-6", **kwargs) -> str:
        response = await self.client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 4096),
            messages=messages,
        )
        return response.content[0].text
```

### 4.3 groq_provider.py (fast inference fallback)

```python
from groq import AsyncGroq
from .base import InferenceProvider

class GroqProvider(InferenceProvider):
    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)

    async def complete(self, messages: list[dict], model: str = "llama-3.1-70b-versatile", **kwargs) -> str:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        return response.choices[0].message.content
```

### 4.4 openai_provider.py (embeddings fallback + Whisper STT API)

```python
from openai import AsyncOpenAI
from .base import EmbeddingProvider, STTProvider

OPENAI_DIMENSIONS = {
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
}

class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def embed(self, texts: list[str], model: str = "text-embedding-3-large") -> list[list[float]]:
        response = await self.client.embeddings.create(input=texts, model=model)
        return [item.embedding for item in response.data]

    def dimensions(self, model: str = "text-embedding-3-large") -> int:
        return OPENAI_DIMENSIONS.get(model, 3072)

class OpenAISTTProvider(STTProvider):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        response = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.mp3", audio_bytes),
            language=language,
        )
        return response.text
```

Stubs for nllb_provider.py, whisper_provider.py, elevenlabs_provider.py: create as empty classes raising `NotImplementedError`. Prompt 231 fills them in.

---

## 5. Shared utilities

### 5.1 utils/chunking.py

```python
import tiktoken
from dataclasses import dataclass

@dataclass
class Chunk:
    text: str
    index: int
    token_count: int
    metadata: dict

def chunk_document(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
    metadata: dict | None = None,
    encoding_name: str = "cl100k_base",
) -> list[Chunk]:
    enc = tiktoken.get_encoding(encoding_name)
    tokens = enc.encode(text)
    chunks = []
    start = 0
    idx = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(Chunk(
            text=chunk_text,
            index=idx,
            token_count=len(chunk_tokens),
            metadata=metadata or {},
        ))
        start = end - overlap_tokens
        idx += 1
    return chunks
```

### 5.2 utils/caching.py

```python
import hashlib, json
import redis.asyncio as redis_async

_redis: redis_async.Redis | None = None

async def init_cache():
    global _redis
    from .config import settings
    _redis = redis_async.from_url(settings.redis_url, decode_responses=False)

def _cache_key(prefix: str, payload: dict) -> str:
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return f"keprix:ml:{prefix}:{h}"

async def get_cached(prefix: str, payload: dict) -> list[float] | None:
    if _redis is None: return None
    key = _cache_key(prefix, payload)
    raw = await _redis.get(key)
    return json.loads(raw) if raw else None

async def set_cached(prefix: str, payload: dict, value, ttl: int = 86400):
    if _redis is None: return
    key = _cache_key(prefix, payload)
    await _redis.setex(key, ttl, json.dumps(value))
```

### 5.3 utils/errors.py

```python
from fastapi import HTTPException

class ProviderError(Exception):
    def __init__(self, provider: str, message: str, status_code: int = 502):
        self.provider = provider
        self.message = message
        self.status_code = status_code
        super().__init__(f"{provider}: {message}")

class ModelNotReadyError(Exception): ...
class UnsupportedLanguageError(Exception): ...
class ClassifierNotTrainedError(Exception): ...
```

---

## 6. TypeScript client package (packages/ml-client)

### 6.1 types.ts

```typescript
export interface EmbedRequest {
  texts: string[]
  model?: string
  pack_id?: string
}

export interface EmbedResponse {
  embeddings: number[][]
  model: string
  token_count: number
}

export interface SearchRequest {
  query: string
  pack_id: string
  top_k?: number
  score_threshold?: number
}

export interface SearchResult {
  text: string
  score: number
  metadata: Record<string, unknown>
}

export interface DetectLanguageRequest { text: string }
export interface DetectLanguageResponse {
  language: string        // BCP-47 code e.g. "tw" (Twi), "ee" (Ewe), "en"
  confidence: number
  script: string
}

export interface TranslateRequest {
  text: string
  src_lang: string        // BCP-47 or "auto"
  tgt_lang: string
}

export interface TranslateResponse {
  translated_text: string
  src_lang: string        // resolved if "auto" was passed
}

export interface TranscribeRequest {
  audio_b64: string       // base64 encoded audio
  mime_type: string       // "audio/ogg", "audio/mp3", "audio/wav"
  language?: string       // hint; "auto" for detection
}

export interface TranscribeResponse {
  text: string
  detected_language?: string
}

export interface ClassifyIntentRequest { text: string; context?: string }
export interface ClassifyIntentResponse {
  intent: string
  confidence: number
  candidates: Array<{ intent: string; confidence: number }>
}

export interface MLServiceHealth {
  status: "ok" | "degraded" | "down"
  providers: Record<string, "ok" | "unavailable">
  models_loaded: string[]
}
```

### 6.2 index.ts (base client)

```typescript
import type { MLServiceHealth } from "./types"

export class MLServiceClient {
  constructor(
    private baseUrl: string = process.env.KEPRIX_ML_SERVICE_URL ?? "http://localhost:8200"
  ) {}

  protected async post<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const err = await res.text()
      throw new Error(`ML service error ${res.status}: ${err}`)
    }
    return res.json() as Promise<T>
  }

  async health(): Promise<MLServiceHealth> {
    const res = await fetch(`${this.baseUrl}/health`)
    return res.json()
  }
}

export { EmbeddingClient } from "./embedding-client"
export { LanguageClient } from "./language-client"
export { ClassifierClient } from "./classifier-client"
export * from "./types"
```

---

## 7. Tool registry entries (TypeScript - keprix tool registry)

Add to the keprix tool registry (location: wherever current tools are registered in the keprix codebase):

```typescript
import { EmbeddingClient, LanguageClient, ClassifierClient } from "@keprix/ml-client"

const ml = {
  embedding: new EmbeddingClient(),
  language: new LanguageClient(),
  classifier: new ClassifierClient(),
}

// Registered tools (implemented in 230-232; stubs here return not_ready)
export const ML_TOOLS = [
  {
    name: "search_domain_knowledge",
    description: "Search the keprix domain knowledge pack for relevant context.",
    parameters: {
      query: { type: "string", required: true },
      pack_id: { type: "string", required: true },
      top_k: { type: "number", default: 5 },
    },
    handler: async (args) => ml.embedding.search(args),
  },
  {
    name: "detect_language",
    description: "Detect the language of a text string. Returns BCP-47 code.",
    parameters: { text: { type: "string", required: true } },
    handler: async (args) => ml.language.detectLanguage(args),
  },
  {
    name: "translate",
    description: "Translate text between languages. Pass src_lang='auto' to detect automatically.",
    parameters: {
      text: { type: "string", required: true },
      src_lang: { type: "string", default: "auto" },
      tgt_lang: { type: "string", required: true },
    },
    handler: async (args) => ml.language.translate(args),
  },
  {
    name: "transcribe_audio",
    description: "Transcribe a voice message or audio clip to text.",
    parameters: {
      audio_b64: { type: "string", required: true },
      mime_type: { type: "string", required: true },
      language: { type: "string", default: "auto" },
    },
    handler: async (args) => ml.language.transcribe(args),
  },
  {
    name: "synthesize_speech",
    description: "Convert text to audio. Returns base64-encoded MP3.",
    parameters: {
      text: { type: "string", required: true },
      language: { type: "string", default: "en" },
      voice_id: { type: "string", default: "default" },
    },
    handler: async (args) => ml.language.synthesize(args),
  },
  {
    name: "classify_intent",
    description: "Classify the intent of an incoming message (e.g. quote, report, dues, complaint).",
    parameters: {
      text: { type: "string", required: true },
      context: { type: "string" },
    },
    handler: async (args) => ml.classifier.classifyIntent(args),
  },
  {
    name: "classify_formation",
    description: "Classify geological formation type from a drilling log description.",
    parameters: { description: { type: "string", required: true } },
    handler: async (args) => ml.classifier.classifyFormation(args),
  },
  {
    name: "predict_yield",
    description: "Predict expected water yield range given formation data and location.",
    parameters: {
      formation: { type: "string", required: true },
      depth_m: { type: "number", required: true },
      gps_lat: { type: "number" },
      gps_lng: { type: "number" },
    },
    handler: async (args) => ml.classifier.predictYield(args),
  },
  {
    name: "check_duplicate_member",
    description: "Check whether a new member registration is a likely duplicate of an existing member.",
    parameters: {
      first_name: { type: "string", required: true },
      last_name: { type: "string", required: true },
      phone: { type: "string" },
      dob: { type: "string" },
    },
    handler: async (args) => ml.classifier.checkDuplicate(args),
  },
  {
    name: "detect_agent_anomaly",
    description: "Score whether an agent action sequence is anomalous relative to its playbook.",
    parameters: {
      agent_id: { type: "string", required: true },
      action_sequence: { type: "array", items: { type: "string" }, required: true },
    },
    handler: async (args) => ml.classifier.detectAnomaly(args),
  },
]
```

---

## 8. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[local]"

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8200"]
```

Add to main docker-compose.yml:

```yaml
  ml-service:
    build: ./apps/ml-service
    ports:
      - "8200:8200"
    env_file: ./apps/ml-service/.env
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8200/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

---

## 9. Environment variables (.env.example)

```
KEPRIX_ML_ANTHROPIC_API_KEY=sk-ant-...
KEPRIX_ML_VOYAGE_API_KEY=pa-...
KEPRIX_ML_OPENAI_API_KEY=sk-...          # optional
KEPRIX_ML_GROQ_API_KEY=gsk_...           # optional
KEPRIX_ML_ELEVENLABS_API_KEY=...         # optional
KEPRIX_ML_REDIS_URL=redis://redis:6379/0
KEPRIX_ML_DATABASE_URL=postgresql://keprix:keprix@postgres:5432/keprix
KEPRIX_ML_ENVIRONMENT=development
KEPRIX_ML_PRIMARY_EMBEDDING_PROVIDER=voyage
KEPRIX_ML_PRIMARY_STT_PROVIDER=openai
KEPRIX_ML_PRIMARY_TRANSLATION_PROVIDER=nllb
```

---

## 10. Health router (routers/health.py)

```python
from fastapi import APIRouter
from ..providers.voyage_provider import VoyageProvider
from ..config import settings

router = APIRouter()

@router.get("")
async def health():
    providers = {}
    try:
        vp = VoyageProvider(settings.voyage_api_key)
        await vp.embed(["ping"], model="voyage-3-lite")
        providers["voyage"] = "ok"
    except Exception:
        providers["voyage"] = "unavailable"

    status = "ok" if all(v == "ok" for v in providers.values()) else "degraded"
    return {"status": status, "providers": providers, "models_loaded": []}
```

---

## 11. Acceptance criteria

1. `docker compose up ml-service` starts without errors
2. `GET /health` returns `{ "status": "ok", "providers": { "voyage": "ok" } }`
3. All 10 tool stubs are registered in the keprix tool registry
4. TypeScript client builds without errors (`pnpm -F @keprix/ml-client build`)
5. Calling any tool stub before 230-232 are implemented returns a structured `not_ready` response rather than a 500
6. Redis cache layer initialises on startup; cache miss returns null without crashing
7. All provider adapters have unit tests covering happy path and provider error handling

---

## 12. Files to read before building

- Current keprix tool registry location (grep for `registerTool` or equivalent in the keprix codebase)
- Existing docker-compose.yml to confirm postgres and redis service names
- Prompt 230 (embeddings) and 231 (language) to understand what the routers must serve
