from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = ""
    google_api_key: Optional[str] = None
    google_client_id: str
    google_client_secret: str
    azure_api_key: str
    azure_endpoint: str
    frontend_app_url: str
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Application settings loaded from environment
    """
    return Settings()  # type: ignore
