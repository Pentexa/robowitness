"""Application configuration and environment settings."""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root (…/backend/..). Relative artifact/DB paths anchor here so
# evidence lands in <repo>/artifacts no matter the process working directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _anchored(path_str: str) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (_REPO_ROOT / p).resolve()

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
        return _anchored(self.RW_ARTIFACTS_DIR)

    @property
    def db_path(self) -> Path:
        return _anchored(self.RW_DB_PATH)

settings = Settings()
