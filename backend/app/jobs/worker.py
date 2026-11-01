"""Dedicated worker process polling SQLite jobs queue."""

import json
import os
import signal
import tempfile
import time
import uuid
from datetime import datetime, timezone
from app.config import settings
from app.db import init_db
from app.jobs.repository import claim_next_job, update_job_progress, update_job_status
from app.jobs.service import JobExecutionService

RUNNING = True
_HEARTBEAT_PATH = settings.artifacts_path / "worker_heartbeat.json"
_LAST_BEAT = 0.0


def write_heartbeat(worker_id: str, force: bool = False) -> None:
    """Record worker liveness for /api/health (throttled, atomic, best-effort)."""
    global _LAST_BEAT
    now = time.time()
    if not force and (now - _LAST_BEAT) < 5.0:
        return
    _LAST_BEAT = now
    try:
        _HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {"worker_id": worker_id, "ts": datetime.now(timezone.utc).isoformat()}
        with tempfile.NamedTemporaryFile(
            "w", dir=str(_HEARTBEAT_PATH.parent), delete=False, encoding="utf-8"
        ) as tf:
            json.dump(payload, tf)
            tmp_name = tf.name
        os.replace(tmp_name, _HEARTBEAT_PATH)
    except Exception as e:
        print(f"[Worker] heartbeat write failed: {e}")


def signal_handler(signum, frame):
    global RUNNING
    print(f"\n[Worker] Received signal {signum}, stopping cooperatively...")
    RUNNING = False


def run_worker_loop(poll_interval_s: float = 0.5):
    global RUNNING
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    worker_id = f"worker-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    print("==================================================")
    print(f"RoboWitness Worker Starting: {worker_id}")
    print("==================================================")

    init_db()
    service = JobExecutionService()

    while RUNNING:
        try:
            write_heartbeat(worker_id)
            job = claim_next_job(worker_id)
            if not job:
                time.sleep(poll_interval_s)
                continue

            print(f"[Worker] Claimed job {job.job_id} (kind={job.kind}, result_id={job.result_id})")
            write_heartbeat(worker_id, force=True)

            if job.kind == "simulation_run":
                service.execute_simulation_run(job)
            elif job.kind == "battery_run":
                service.execute_battery_run(
                    job, progress_callback=lambda p: update_job_progress(job.job_id, p)
                )
            elif job.kind == "verification":
                service.execute_verification(
                    job, progress_callback=lambda p: update_job_progress(job.job_id, p)
                )

            update_job_status(job.job_id, status="completed", finished=True)
            print(f"[Worker] Completed job {job.job_id}")

        except Exception as e:
            print(f"[Worker] Error processing job: {e}")
            if "job" in locals() and job:
                update_job_status(job.job_id, status="failed", error_code=str(e), finished=True)
            time.sleep(poll_interval_s)

    print("[Worker] Exited cleanly.")


if __name__ == "__main__":
    run_worker_loop()
