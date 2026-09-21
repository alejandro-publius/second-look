"""Settings from the environment. Read once. Never log secrets."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_SECRET = "change-me-long-random"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/local.db"
    export_token: str = PLACEHOLDER_SECRET
    qa_key: str = PLACEHOLDER_SECRET
    public_web_origin: str = "http://localhost:3000"
    api_origin: str = "http://localhost:8000"
    rainfall_dry_mm: float = 2.5
    rainfall_window_hours: int = 72
    checker_enabled: bool = False
    sandbox_base_url: str = "https://sandbox.hl7europe.eu/oneaquahealth/fhir"
    sandbox_mirror_enabled: bool = False
    repo_url: str = "https://github.com/alejandro-publius/second-look"
    # Set by the deploy step to the git commit being served. Stored with every session.
    build_hash: str = "dev"
    # Where content/ and photos/ live. The repo root in development and in the container.
    content_root: str = "."
    # Private folder for re-encoded uploads. Never served as static files.
    upload_dir: str = "./data/uploads"
    audit_log_path: str = "./audit/log.jsonl"
    # Empty means the API makes one at first use and keeps it in the randomization counter row.
    randomization_seed: str = ""

    def secret_is_usable(self, value: str) -> bool:
        """A secret left at its placeholder, or too short, is treated as not set at all."""
        return value != PLACEHOLDER_SECRET and len(value) >= 16


settings = Settings()
