"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for DayShield backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "DayShield API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    simulation_mode: bool = True
    user_timezone: str = "Asia/Kolkata"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080"

    # Gemini / Google ADK
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Google OAuth 2.0 (Phase 3)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/integrations/google/callback"

    # Database (Phase 4)
    database_url: str = "sqlite:///./dayshield.db"

    # Security (Phase 4)
    secret_key: str = "dayshield-dev-secret-change-in-production"
    approval_token_ttl_seconds: int = 900  # 15 minutes

    # Working hours for deterministic validation (24h format)
    work_hours_start: int = 8
    work_hours_end: int = 20

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
