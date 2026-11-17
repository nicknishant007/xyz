"""Central environment-backed configuration and external service URLs."""
from functools import lru_cache
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
    agent_concurrency: int = 5
    sync_max_threads: int = 200
    session_secret: str = "development-only-change-me"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
