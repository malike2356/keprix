from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://keys:keys@localhost:5433/keys_server"
    key_server_jwt_secret: str = "dev-jwt-secret"
    key_server_checksum_secret: str = "dev-checksum-secret"
    admin_token: str = "dev-admin-token"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    scout_provision_url: str = "http://localhost:4444/api/internal/provision-tenant"
    scout_provision_secret: str = ""
    scout_console_public_url: str = "https://console.labyrinthscout.com"
    resend_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    email_from: str = "contact@verlox.uk"


settings = Settings()
