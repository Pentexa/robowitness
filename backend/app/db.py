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


def init_db(db_path: Path = None) -> None:
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.executescript(SCHEMA_SQL)
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
