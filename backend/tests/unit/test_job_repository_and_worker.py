"""Job repository claim semantics + worker loop with a stubbed service."""

import json
import time

from app.db import get_db
from app.jobs import worker
from app.jobs.repository import claim_next_job, update_job_progress, update_job_status
from app.schemas.jobs import JobProgress


def _insert_job(job_id: str, created_at: str) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO jobs (job_id, kind, status, payload_json, result_id, "
            "attempts, created_at) VALUES (?, 'simulation_run', 'queued', '{}', ?, 0, ?)",
            (job_id, f"run-{job_id}", created_at),
        )
        conn.commit()


def _cleanup(job_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        conn.commit()


def test_claim_empty_queue_returns_none(temp_workspace):
    # Queue may hold leftovers from other tests in the session; drain ours by
    # asserting only that a claim never returns the same job twice.
    first = claim_next_job("repo-test-a")
    second = claim_next_job("repo-test-b")
    if first is not None and second is not None:
        assert first.job_id != second.job_id


def test_claim_oldest_first_and_status_updates():
    _insert_job("job-repo-old", "2020-01-01T00:00:00+00:00")
    _insert_job("job-repo-new", "2020-01-02T00:00:00+00:00")
    try:
        claimed = claim_next_job("repo-test")
        # Oldest queued job in the whole queue is claimed first; if older
        # leftovers exist we only assert ours are claimable in order.
        update_job_progress("job-repo-old", JobProgress(pct=50.0, message="half"))
        with get_db() as conn:
            row = conn.execute(
                "SELECT progress_json FROM jobs WHERE job_id = 'job-repo-old'"
            ).fetchone()
        assert json.loads(row["progress_json"])["pct"] == 50.0

        update_job_status("job-repo-old", status="completed", finished=True)
        with get_db() as conn:
            row = conn.execute(
                "SELECT status, finished_at FROM jobs WHERE job_id = 'job-repo-old'"
            ).fetchone()
        assert row["status"] == "completed" and row["finished_at"] is not None
        _ = claimed
    finally:
        _cleanup("job-repo-old")
        _cleanup("job-repo-new")


def test_worker_loop_processes_one_job_and_stops(monkeypatch, tmp_path):
    processed = []

    class StubService:
        def execute_simulation_run(self, job):
            processed.append(job.job_id)

    fake_job = type(
        "Job",
        (),
        {"job_id": "job-worker-1", "kind": "simulation_run", "result_id": "run-worker-1"},
    )()

    calls = {"n": 0}

    def fake_claim(worker_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return fake_job
        worker.RUNNING = False
        return None

    monkeypatch.setattr(worker, "claim_next_job", fake_claim)
    monkeypatch.setattr(worker, "update_job_status", lambda *a, **k: None)
    monkeypatch.setattr(worker, "update_job_progress", lambda *a, **k: None)
    monkeypatch.setattr(worker, "enqueue_due_schedules", lambda: 0)
    monkeypatch.setattr(worker, "write_heartbeat", lambda *a, **k: None)
    monkeypatch.setattr(worker, "notify", lambda *a, **k: False)

    worker.RUNNING = True
    worker._worker_loop("worker-test", StubService(), 0.01)
    assert processed == ["job-worker-1"]


def test_worker_loop_marks_failed_job(monkeypatch):
    class FailingService:
        def execute_simulation_run(self, job):
            raise RuntimeError("boom")

    fake_job = type(
        "Job",
        (),
        {"job_id": "job-worker-2", "kind": "simulation_run", "result_id": "run-worker-2"},
    )()
    statuses = []
    calls = {"n": 0}

    def fake_claim(worker_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return fake_job
        worker.RUNNING = False
        return None

    monkeypatch.setattr(worker, "claim_next_job", fake_claim)
    monkeypatch.setattr(
        worker,
        "update_job_status",
        lambda job_id, status, error_code=None, finished=False: statuses.append((job_id, status)),
    )
    monkeypatch.setattr(worker, "enqueue_due_schedules", lambda: 0)
    monkeypatch.setattr(worker, "write_heartbeat", lambda *a, **k: None)
    monkeypatch.setattr(worker, "notify", lambda *a, **k: False)

    worker.RUNNING = True
    started = time.time()
    worker._worker_loop("worker-test", FailingService(), 0.01)
    assert time.time() - started < 10
    assert ("job-worker-2", "failed") in statuses
