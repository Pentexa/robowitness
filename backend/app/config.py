"""Application configuration and environment settings."""

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
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        extra="ignore",
    )

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
    # Local user policy plugins (İş 3B): OFF by default. When "on", the user may
    # run THEIR OWN single-file Python policy in an isolated subprocess during
    # simulation. AI-generated code must never be used with this; it is not a
    # security sandbox — only run code you wrote and trust.
    RW_ALLOW_LOCAL_POLICY: str = "off"
    # Enterprise auth (opt-in): "key:role:workspace;key2:viewer:ws" — empty = open local mode.
    RW_API_KEYS: str = ""
    # JWT bearer auth (opt-in): HS256 shared secret and/or OIDC JWKS (RS256).
    RW_JWT_SECRET: str = ""
    RW_OIDC_JWKS_URL: str = ""
    RW_OIDC_ISSUER: str = ""
    RW_OIDC_AUDIENCE: str = ""
    # Enterprise hardening: per-actor requests/minute (0 = off), webhooks.
    RW_RATE_LIMIT_PER_MIN: int = 0
    RW_WEBHOOK_URL: str = ""
    RW_WEBHOOK_SECRET: str = ""
    RW_WORKER_CONCURRENCY: int = 1
    # Sensor model: "legacy" (exact delayed geometry, default; all measured
    # results in the docs use this) or "beam" (24-ray LiDAR-like casting:
    # obstacles are only seen when a ray actually hits them, with quantized
    # bearing). Beam mode is experimental and changes outcomes by design.
    RW_SENSOR_MODEL: str = "legacy"
    # Candidate law: "shared" (stateless, default; all frozen results),
    # "mpc" (verified MPC-lite, opt-in), "mpc-crowd" (crowd-tuned variant),
    # or the experimental "stateful" / "waypoint" planners (candidate-only).
    RW_CANDIDATE_LAW: str = "shared"
    RW_DB_PATH: str = "./artifacts/robowitness.sqlite3"
    RW_ARTIFACTS_DIR: str = "./artifacts"
    RW_CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def local_policy_enabled(self) -> bool:
        return self.RW_ALLOW_LOCAL_POLICY.strip().lower() in ("on", "true", "1", "yes")

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
