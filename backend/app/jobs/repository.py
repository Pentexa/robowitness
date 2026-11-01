"""Jobs persistence repository with atomic SQLite claim."""

from datetime import datetime, timezone
from typing import Optional
from app.db import get_db
from app.schemas.jobs import JobProgress, JobRecord


def claim_next_job(worker_id: str) -> Optional[JobRecord]:
    """Atomically claim the oldest queued job using BEGIN IMMEDIATE."""
    with get_db() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if not row:
                conn.commit()
                return None

            job_id = row["job_id"]
            now = datetime.now(timezone.utc).isoformat()

            conn.execute(
                """
                UPDATE jobs
                SET status = 'running', started_at = ?, lease_owner = ?
                WHERE job_id = ?
                """,
                (now, worker_id, job_id),
            )
            conn.commit()

            return JobRecord(
                job_id=row["job_id"],
                kind=row["kind"],
                status="running",
                payload_json=row["payload_json"],
                result_id=row["result_id"],
                attempts=row["attempts"] + 1,
                created_at=row["created_at"],
                started_at=now,
                lease_owner=worker_id,
            )
        except Exception:
            conn.rollback()
            raise


def update_job_progress(job_id: str, progress: JobProgress) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET progress_json = ? WHERE job_id = ?",
            (progress.model_dump_json(), job_id),
        )
        conn.commit()


def update_job_status(
    job_id: str, status: str, error_code: Optional[str] = None, finished: bool = False
) -> None:
    now = datetime.now(timezone.utc).isoformat() if finished else None
    with get_db() as conn:
        if finished:
            conn.execute(
                "UPDATE jobs SET status = ?, finished_at = ?, error_code = ? WHERE job_id = ?",
                (status, now, error_code, job_id),
            )
        else:
            conn.execute(
                "UPDATE jobs SET status = ?, error_code = ? WHERE job_id = ?",
                (status, error_code, job_id),
            )
        conn.commit()
