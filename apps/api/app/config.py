from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+psycopg://finpass:finpass@localhost:5432/finpass"
    openai_api_key: str | None = None
    openai_model: str | None = None

    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
