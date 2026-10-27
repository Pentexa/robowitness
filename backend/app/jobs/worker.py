"""Dedicated worker process polling SQLite jobs queue."""
import os
import signal
import sys
import time
import uuid
from app.db import init_db
from app.jobs.repository import claim_next_job, update_job_progress, update_job_status
from app.jobs.service import JobExecutionService

RUNNING = True

def signal_handler(signum, frame):
    global RUNNING
    print(f"\n[Worker] Received signal {signum}, stopping cooperatively...")
    RUNNING = False

def run_worker_loop(poll_interval_s: float = 0.5):
    global RUNNING
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    worker_id = f"worker-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    print(f"==================================================")
    print(f"RoboWitness Worker Starting: {worker_id}")
    print(f"==================================================")

    init_db()
    service = JobExecutionService()

    while RUNNING:
        try:
            job = claim_next_job(worker_id)
            if not job:
                time.sleep(poll_interval_s)
                continue

            print(f"[Worker] Claimed job {job.job_id} (kind={job.kind}, result_id={job.result_id})")

            if job.kind == "simulation_run":
                service.execute_simulation_run(job)
            elif job.kind == "verification":
                service.execute_verification(
                    job,
                    progress_callback=lambda p: update_job_progress(job.job_id, p)
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
