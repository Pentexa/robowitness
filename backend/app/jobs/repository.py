"""Jobs persistence repository with atomic SQLite claim and lease recovery."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from app.config import settings
from app.db import get_db
from app.schemas.jobs import JobProgress, JobRecord


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lease_until() -> str:
    return (_now() + timedelta(seconds=settings.RW_JOB_LEASE_SECONDS)).isoformat()


def reclaim_expired_jobs(conn) -> int:
    """Return jobs whose worker died mid-flight (lease expired) to the queue."""
    now = _now().isoformat()
    cursor = conn.execute(
        """
        UPDATE jobs
        SET status = 'queued', lease_owner = NULL, lease_until = NULL, started_at = NULL
        WHERE status = 'running' AND lease_until IS NOT NULL AND lease_until < ?
        """,
        (now,),
    )
    return cursor.rowcount


def claim_next_job(worker_id: str) -> Optional[JobRecord]:
    """Atomically claim the oldest queued job using BEGIN IMMEDIATE.

    Expired leases are reclaimed first, so a job whose worker crashed is
    retried by the next worker instead of hanging in 'running' forever.
    """
    with get_db() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            reclaim_expired_jobs(conn)
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
            now = _now().isoformat()

            conn.execute(
                """
                UPDATE jobs
                SET status = 'running', started_at = ?, lease_owner = ?,
                    lease_until = ?, attempts = attempts + 1
                WHERE job_id = ?
                """,
                (now, worker_id, _lease_until(), job_id),
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
    """Record progress and renew the lease (long jobs stay owned)."""
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET progress_json = ?, lease_until = ? WHERE job_id = ?",
            (progress.model_dump_json(), _lease_until(), job_id),
        )
        conn.commit()


def renew_lease(job_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET lease_until = ? WHERE job_id = ? AND status = 'running'",
            (_lease_until(), job_id),
        )
        conn.commit()


def update_job_status(
    job_id: str, status: str, error_code: Optional[str] = None, finished: bool = False
) -> None:
    now = _now().isoformat() if finished else None
    with get_db() as conn:
        if finished:
            conn.execute(
                "UPDATE jobs SET status = ?, finished_at = ?, error_code = ?, "
                "lease_owner = NULL, lease_until = NULL WHERE job_id = ?",
                (status, now, error_code, job_id),
            )
        else:
            conn.execute(
                "UPDATE jobs SET status = ?, error_code = ? WHERE job_id = ?",
                (status, error_code, job_id),
            )
        conn.commit()
