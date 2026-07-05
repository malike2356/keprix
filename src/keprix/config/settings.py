"""Runtime configuration loaded from environment variables.

All Keprix-specific variables use the KEPRIX_ prefix.
Provider API keys use their canonical upstream names (OPENAI_API_KEY, etc.)
so the same .env works with local model servers without modification.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------ server
    BACKEND_BIND: str = "127.0.0.1"
    BACKEND_PORT: int = 3333
    FRONTEND_BIND: str = "127.0.0.1"
    FRONTEND_PORT: int = 3000

    # ------------------------------------------------------------------ database
    KEPRIX_DATABASE_URL: str = "postgresql+asyncpg://keprix:changeme@localhost:5432/keprix"

    # ------------------------------------------------------------------ redis
    KEPRIX_REDIS_URL: str = "redis://:changeme@localhost:6379"

    # ------------------------------------------------------------------ auth
    KEPRIX_JWT_SECRET: str = Field(default="CHANGE_ME", min_length=32)
    KEPRIX_SESSION_SECRET: str = Field(default="CHANGE_ME", min_length=32)
    KEPRIX_TOTP_ISSUER: str = "Keprix"
    KEPRIX_ALLOWED_ORIGINS: str = "http://localhost:3000"
    KEPRIX_SECURE_COOKIES: bool = False
    KEPRIX_ADMIN_PASSWORD: str = ""

    # ------------------------------------------------------------------ developer mode
    KEPRIX_DEVELOPER_MODE: bool = False

    # ------------------------------------------------------------------ llm providers
    KEPRIX_DEFAULT_PROVIDER: str = "auto"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    TOGETHER_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434/v1"
    LM_STUDIO_URL: str = "http://host.docker.internal:1234/v1"
    CUSTOM_LLM_BASE_URL: str = ""
    CUSTOM_LLM_API_KEY: str = ""

    # ------------------------------------------------------------------ memory / rag
    KEPRIX_CHROMADB_HOST: str = "localhost"
    KEPRIX_CHROMADB_PORT: int = 8100
    KEPRIX_EMBEDDING_URL: str = ""
    KEPRIX_EMBEDDING_API_KEY: str = ""
    KEPRIX_EMBEDDING_MODEL: str = "text-embedding-3-small"
    KEPRIX_FASTEMBED_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    KEPRIX_FASTEMBED_CACHE_PATH: str = ""

    # ------------------------------------------------------------------ web search
    KEPRIX_SEARXNG_URL: str = "http://localhost:8080"

    # ------------------------------------------------------------------ channels
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""
    DISCORD_BOT_TOKEN: str = ""
    DISCORD_APPLICATION_ID: str = ""

    # ------------------------------------------------------------------ email
    KEPRIX_SMTP_HOST: str = ""
    KEPRIX_SMTP_PORT: int = 587
    KEPRIX_SMTP_USER: str = ""
    KEPRIX_SMTP_PASS: str = ""
    KEPRIX_EMAIL_FROM: str = ""
    KEPRIX_RESEND_API_KEY: str = ""

    # ------------------------------------------------------------------ imap
    KEPRIX_IMAP_HOST: str = ""
    KEPRIX_IMAP_PORT: int = 993
    KEPRIX_IMAP_USER: str = ""
    KEPRIX_IMAP_PASS: str = ""

    # ------------------------------------------------------------------ calendar
    KEPRIX_GOOGLE_CLIENT_ID: str = ""
    KEPRIX_GOOGLE_CLIENT_SECRET: str = ""
    KEPRIX_GOOGLE_REDIRECT_URI: str = "http://localhost:3000/oauth/google/callback"
    KEPRIX_CALDAV_URL: str = ""
    KEPRIX_CALDAV_USERNAME: str = ""
    KEPRIX_CALDAV_PASSWORD: str = ""

    # ------------------------------------------------------------------ vault
    KEPRIX_VAULT_KEY: str = Field(default="CHANGE_ME_32_CHARS______________", min_length=32)

    # ------------------------------------------------------------------ mcp
    KEPRIX_MCP_ALLOWED_SERVERS: str = ""

    # ------------------------------------------------------------------ scout connector
    KEPRIX_SCOUT_API_KEY: str = ""
    KEPRIX_SCOUT_WORKSPACE_ID: str = ""
    KEPRIX_SCOUT_ENDPOINT: str = "https://api.labyrinthscout.com"
    KEPRIX_SCOUT_ENABLED: bool = False

    # ------------------------------------------------------------------ mutation engine
    KEPRIX_GENERATED_TOOLS_DIR: str = "/data/keprix/generated/tools"
    KEPRIX_GENERATED_SKILLS_DIR: str = "/data/keprix/generated/skills"
    KEPRIX_SANDBOX_TIMEOUT: int = 30
    KEPRIX_MUTATION_REQUIRE_APPROVAL: bool = True
    KEPRIX_MUTATION_RATE_LIMIT: int = 10

    # ------------------------------------------------------------------ observability
    KEPRIX_LOG_LEVEL: Literal["debug", "info", "warning", "error"] = "info"
    KEPRIX_OTLP_ENDPOINT: str = ""

    # ------------------------------------------------------------------ data dirs
    KEPRIX_DATA_DIR: str = "/data/keprix"
    KEPRIX_LOGS_DIR: str = "/data/keprix/logs"

    # ------------------------------------------------------------------ upload limits (bytes)
    KEPRIX_CHAT_UPLOAD_MAX_BYTES: int = 10_485_760      # 10 MB
    KEPRIX_DOCUMENT_UPLOAD_MAX_BYTES: int = 26_214_400  # 25 MB
    KEPRIX_AUDIO_UPLOAD_MAX_BYTES: int = 26_214_400     # 25 MB

    # ------------------------------------------------------------------ cleanup
    KEPRIX_CLEANUP_INTERVAL_HOURS: int = 24

    @field_validator("KEPRIX_ALLOWED_ORIGINS")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.KEPRIX_ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def database_url_sync(self) -> str:
        """Synchronous SQLAlchemy URL (for Alembic migrations)."""
        return self.KEPRIX_DATABASE_URL.replace("+asyncpg", "")

    @property
    def mcp_allowed_servers_list(self) -> list[str]:
        if not self.KEPRIX_MCP_ALLOWED_SERVERS:
            return []
        return [s.strip() for s in self.KEPRIX_MCP_ALLOWED_SERVERS.split(",") if s.strip()]


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
