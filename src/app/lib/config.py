from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    database_url: str = ""
    google_api_key: Optional[str] = None
    google_client_id: str
    google_client_secret: str
    azure_inference_credential: str
    azure_inference_endpoint: str

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
