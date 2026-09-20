"""Settings from the environment. Never log secrets."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/local.db"
    export_token: str = "change-me-long-random"
    qa_key: str = "change-me-long-random"
    public_web_origin: str = "http://localhost:3000"
    api_origin: str = "http://localhost:8000"
    rainfall_dry_mm: float = 2.5
    rainfall_window_hours: int = 72
    checker_enabled: bool = False
    sandbox_base_url: str = "https://sandbox.hl7europe.eu/oneaquahealth/fhir"
    sandbox_mirror_enabled: bool = False
    repo_url: str = "https://github.com/alejandro-publius/second-look"


settings = Settings()
