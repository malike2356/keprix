"""ApplicationContext configuration via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from keprix.config.constants import PRODUCT_NAME, PRODUCT_VERSION


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KEPRIX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    product_name: str = PRODUCT_NAME
    product_version: str = PRODUCT_VERSION
    database_url: str = "postgresql+asyncpg://keprix:changeme@localhost:5432/keprix"
    redis_url: str = "redis://localhost:6379/0"
    allowed_origins: str = ""
    session_ttl_days: int = 7
    require_2fa: bool = False
    ip_hash_salt: str = ""
    csp_extra: str = ""
    redact_private_ips: bool = False
    audit_fail_on_high: bool = False
    secure_cookies: bool = False
    developer_mode: bool = False
    jwt_secret: str = ""
    session_secret: str = ""
    totp_issuer: str = "Keprix"

    mutation_enabled: bool = True
    mutation_tool_synthesis: bool = True
    mutation_prompt_evolution: bool = False
    mutation_self_coding: bool = False
    mutation_auto_approve_threshold: float = 0.85
    mutation_require_tests: bool = True
    mutation_generated_tools_dir: str = ""
    mutation_retention_days: int = 365
    mutation_max_generated_tools: int = 200
    mutation_prune_after_days: int = 90

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
