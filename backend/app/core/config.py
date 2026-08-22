from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PashuSafe API"
    environment: str = "development"  # "development" | "production"
    database_url: str = "sqlite:///./pashusafe.db"
    jwt_secret: str = "dev-secret-change-me-before-you-ship-32-bytes!"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
