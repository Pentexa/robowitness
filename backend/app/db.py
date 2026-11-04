"""SQLite database initialization and connection management."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from app.config import settings

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    result_id TEXT,
    attempts INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    lease_owner TEXT,
    lease_until TEXT,
    error_code TEXT,
    progress_json TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    job_id TEXT,
    scenario_hash TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    oracle_status TEXT NOT NULL,
    reason_codes_json TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    artifact_dir TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
);

CREATE TABLE IF NOT EXISTS verifications (
    verification_id TEXT PRIMARY KEY,
    job_id TEXT,
    baseline_run_id TEXT NOT NULL,
    candidate_policy_json TEXT NOT NULL,
    verdict TEXT NOT NULL,
    gates_json TEXT NOT NULL,
    artifact_dir TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id),
    FOREIGN KEY(baseline_run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS api_keys (
    key_id TEXT PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    role_name TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    idem_key TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS battery_schedules (
    schedule_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    robot_id TEXT NOT NULL,
    policy_json TEXT NOT NULL,
    local_policy TEXT,
    scenario_ids_json TEXT NOT NULL,
    interval_minutes INTEGER NOT NULL,
    next_run_at TEXT NOT NULL,
    last_run_at TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    role_name TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS policy_profiles (
    profile_id TEXT PRIMARY KEY,
    profile_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS battery_runs (
    battery_id TEXT PRIMARY KEY,
    robot_id TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stress_runs (
    stress_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS adversarial_runs (
    adversarial_id TEXT PRIMARY KEY,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS telemetry_imports (
    import_id TEXT PRIMARY KEY,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS robots (
    robot_id TEXT PRIMARY KEY,
    profile_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_requests (
    request_id TEXT PRIMARY KEY,
    prompt_hash TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
"""


_WORKSPACE_TABLES = (
    "robots",
    "policy_profiles",
    "battery_runs",
    "telemetry_imports",
    "stress_runs",
    "adversarial_runs",
)


def _migrate_workspace_columns(conn: sqlite3.Connection) -> None:
    """Add workspace_id to tenant tables created before tenancy existed."""
    for table in _WORKSPACE_TABLES:
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if cols and "workspace_id" not in cols:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN workspace_id TEXT NOT NULL DEFAULT 'default'"
            )


def init_db(db_path: Path = None) -> None:
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.executescript(SCHEMA_SQL)
        _migrate_workspace_columns(conn)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db(db_path: Path = None) -> Generator[sqlite3.Connection, None, None]:
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()
