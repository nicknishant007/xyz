"""Central environment-backed configuration and external service URLs."""
from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gmail AI Mail Manager"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    api_v1_prefix: str = "/api"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    cookie_secure: bool = False

    mock_integrations: bool = True
    mock_gmail_api_url: str = "http://localhost:8000/mock/gmail"
    mock_ai_api_url: str = "http://localhost:8000/mock/ai"
    google_api_base_url: str = "https://gmail.googleapis.com/gmail/v1"
    google_oauth_base_url: str = "https://accounts.google.com"
    gemini_api_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    database_url: str = "sqlite:///./mail_manager.db"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    agent_concurrency: int = Field(default=5, ge=1, le=32)
    sync_max_threads: int = Field(default=200, ge=1, le=500)
    session_secret: str = "development-only-change-me"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.app_env.lower() == "production":
            if self.mock_integrations:
                raise ValueError("Mock integrations must be disabled in production.")
            if self.session_secret in {
                "development-only-change-me",
                "change-this-development-secret",
            } or len(self.session_secret) < 32:
                raise ValueError("Production requires a unique SESSION_SECRET of at least 32 characters.")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production.")
            if not self.google_client_id or not self.google_client_secret:
                raise ValueError("Google OAuth credentials are required in production.")
            if not self.frontend_url.startswith("https://") or not self.google_redirect_uri.startswith("https://"):
                raise ValueError("Production frontend and OAuth redirect URLs must use HTTPS.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
