from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://musicscope:musicscope@localhost:5432/musicscope"
    audio_storage_dir: str = "storage/audio"
    separator_python: str = ".audio-venv312/bin/python"
    separator_executable: str = ".audio-venv312/bin/demucs-infer"
    separator_model: str = "htdemucs"
    separator_checkpoint: str = "955717e8-8726e21a.th"
    separator_package: str = "demucs-infer"
    separator_package_version: str = "4.2.0"
    separator_device: str = "auto"
    audio_max_upload_bytes: int = 250 * 1024 * 1024
    audio_max_duration_seconds: int = 15 * 60
    concert_provider: str = "demo"
    ticketmaster_api_key: str | None = None
    concert_cache_hours: int = 6
    concert_request_timeout_seconds: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
