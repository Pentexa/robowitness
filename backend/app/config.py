"""Application configuration and environment settings."""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    RW_META_API_KEY: str = ""
    RW_META_BASE_URL: str = ""
    RW_META_MODEL: str = ""
    RW_AI_MODE: str = "offline"  # 'offline' or 'live'
    RW_AI_TIMEOUT_SECONDS: int = 20
    RW_AI_MAX_RETRIES: int = 2
    RW_AI_MAX_INPUT_CHARS: int = 16000
    RW_AI_MAX_OUTPUT_TOKENS: int = 1000
    RW_AI_MAX_CALLS_PER_WORKFLOW: int = 3
    RW_AI_MAX_ESTIMATED_COST_USD: float = 1.00
    RW_DB_PATH: str = "./artifacts/robowitness.sqlite3"
    RW_ARTIFACTS_DIR: str = "./artifacts"
    RW_CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.RW_CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def artifacts_path(self) -> Path:
        return Path(self.RW_ARTIFACTS_DIR).resolve()

    @property
    def db_path(self) -> Path:
        return Path(self.RW_DB_PATH).resolve()

settings = Settings()
