from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings
from dependencies import set_classifier_service, set_embedding_service, set_language_service
from providers.elevenlabs_provider import ElevenLabsProvider
from providers.local_provider import (
    DeterministicEmbeddingProvider,
    EchoTranslationProvider,
    SilentTTSProvider,
    TextBytesSTTProvider,
)
from providers.nllb_provider import NLLBProvider
from providers.openai_provider import OpenAIEmbeddingProvider, OpenAISTTProvider
from providers.voyage_provider import VoyageProvider
from providers.whisper_provider import WhisperLocalProvider
from routers import classifiers, embeddings, health, language
from services.classifier_service import ClassifierService
from services.embedding_service import EmbeddingService
from services.language_service import LanguageService
from utils.caching import close_cache, init_cache
from utils.logging import configure_logging

_db_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db_pool
    configure_logging(settings.log_level)
    await init_cache(settings.redis_url)
    try:
        import asyncpg

        _db_pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
        if settings.primary_embedding_provider == "voyage" and settings.voyage_api_key:
            provider = VoyageProvider(settings.voyage_api_key)
        elif settings.openai_api_key:
            provider = OpenAIEmbeddingProvider(settings.openai_api_key)
        else:
            provider = DeterministicEmbeddingProvider()
        set_embedding_service(EmbeddingService(provider, _db_pool))
    except Exception:
        set_embedding_service(None)
    try:
        if settings.primary_stt_provider == "local":
            stt_provider = WhisperLocalProvider(settings.whisper_model_path)
        elif settings.openai_api_key:
            stt_provider = OpenAISTTProvider(settings.openai_api_key)
        else:
            stt_provider = TextBytesSTTProvider()

        tts_provider = (
            ElevenLabsProvider(settings.elevenlabs_api_key)
            if settings.elevenlabs_api_key
            else SilentTTSProvider()
        )
        translator = (
            NLLBProvider(settings.nllb_service_url)
            if settings.primary_translation_provider == "nllb"
            else EchoTranslationProvider()
        )
        set_language_service(LanguageService(stt=stt_provider, tts=tts_provider, translator=translator))
    except Exception:
        set_language_service(None)
    set_classifier_service(ClassifierService(db_pool=_db_pool, model_dir=settings.classifier_model_dir))
    yield
    if _db_pool is not None:
        await _db_pool.close()
    await close_cache()


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
