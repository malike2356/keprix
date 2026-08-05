from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="KEPRIX_ML_", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8200
    log_level: str = "INFO"
    environment: Literal["development", "production"] = "development"

    anthropic_api_key: str = ""
    voyage_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""
    elevenlabs_api_key: str = ""

    redis_url: str = "redis://localhost:6379/0"
    embedding_cache_ttl_seconds: int = 86400

    primary_llm_provider: Literal["anthropic", "openai", "groq"] = "anthropic"
    primary_embedding_provider: Literal["voyage", "openai"] = "voyage"
    primary_stt_provider: Literal["openai", "local"] = "openai"
    primary_tts_provider: Literal["elevenlabs", "local"] = "elevenlabs"
    primary_translation_provider: Literal["nllb", "google"] = "nllb"
    nllb_service_url: str = "http://nllb-service:8210"

    whisper_model_path: str = "models/whisper-medium"
    nllb_model_path: str = "models/nllb-200-distilled-600M"
    classifier_model_dir: str = "models/classifiers"
    database_url: str = "postgresql://localhost:5432/keprix"


settings = Settings()
