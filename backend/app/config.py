from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://farmer:farmer@db:5432/growth"
    jwt_secret: str = "demo-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    llm_enabled: bool = True
    openrouter_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openai/gpt-4o-mini"

    effect_threshold: float = 300.0
    confidence_threshold: float = 0.5


@lru_cache
def get_settings() -> Settings:
    return Settings()
