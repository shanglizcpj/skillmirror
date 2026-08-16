from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SkillMirror API"
    app_version: str = "0.2.0"
    frontend_origin: str = "http://localhost:5173"

    database_url: str = "sqlite:///./skillmirror.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    sandbox_image: str = (
        "skillmirror-python-sandbox:latest"
    )

    sandbox_memory: str = "128m"
    sandbox_cpus: str = "0.5"
    sandbox_pids_limit: int = 64
    sandbox_timeout_seconds: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()