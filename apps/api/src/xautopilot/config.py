from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    database_url: str = "postgresql+asyncpg://xautopilot:xautopilot@localhost:5432/xautopilot"
    secret_key: str = "dev-secret-change-in-production"
    token_encryption_key: str = ""
    access_token_expire_minutes: int = 15
    cors_origins: list[str] = ["http://localhost:3000"]
    frontend_url: str = "http://localhost:3000"
    x_api_mode: str = "mock"  # mock | live
    x_api_base_url: str = "https://api.x.com/2"
    x_oauth_authorize_url: str = "https://twitter.com/i/oauth2/authorize"
    x_oauth_token_url: str = "https://api.x.com/2/oauth2/token"
    x_client_id: str = ""
    x_client_secret: str = ""
    x_redirect_uri: str = "http://localhost:3000/settings/x/callback"
    x_oauth_scopes: str = "tweet.read tweet.write users.read offline.access"
    llm_mode: str = "mock"  # mock | live
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    llm_daily_budget_usd: float = 5.0
    worker_enabled: bool = True
    worker_tick_interval_seconds: int = 60
    worker_manual_tick_enabled: bool = True
    worker_cron_secret: str = ""


settings = Settings()
