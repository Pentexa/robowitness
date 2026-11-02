"""Hardening tests: lease recovery, concurrent claims, hostile inputs, 500s."""

import threading
from datetime import datetime, timedelta, timezone

from app.db import get_db
from app.jobs.repository import claim_next_job


def _insert(job_id: str, status: str = "queued", lease_until: str | None = None) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO jobs (job_id, kind, status, payload_json, result_id, "
            "attempts, created_at, lease_until) VALUES (?, 'simulation_run', ?, '{}', ?, 0, "
            "'2020-01-01T00:00:00+00:00', ?)",
            (job_id, status, f"run-{job_id}", lease_until),
        )
        conn.commit()


def _delete(job_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        conn.commit()


def _status(job_id: str) -> str:
    with get_db() as conn:
        return conn.execute("SELECT status FROM jobs WHERE job_id = ?", (job_id,)).fetchone()[0]


def test_expired_lease_job_is_reclaimed_and_reclaimed_attempts_count():
    expired = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    _insert("job-hard-expired", status="running", lease_until=expired)
    try:
        # Drain the queue until we reach our reclaimed job (older ones first).
        claimed_ids = []
        for _ in range(30):
            job = claim_next_job("hardening-test")
            if job is None:
                break
            claimed_ids.append(job.job_id)
            if job.job_id == "job-hard-expired":
                assert job.attempts >= 1
                break
        assert "job-hard-expired" in claimed_ids
        assert _status("job-hard-expired") == "running"  # now owned by us
    finally:
        _delete("job-hard-expired")


def test_fresh_lease_job_is_not_reclaimed():
    fresh = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    _insert("job-hard-fresh", status="running", lease_until=fresh)
    try:
        # Claiming other work must not steal the freshly-leased job.
        for _ in range(5):
            job = claim_next_job("hardening-test-2")
            if job is None:
                break
            assert job.job_id != "job-hard-fresh"
        assert _status("job-hard-fresh") == "running"
    finally:
        _delete("job-hard-fresh")


def test_concurrent_claims_never_double_claim():
    ids = [f"job-hard-conc-{i}" for i in range(10)]
    for job_id in ids:
        _insert(job_id)
    claimed: list[str] = []
    lock = threading.Lock()

    def worker(n: int) -> None:
        while True:
            job = claim_next_job(f"conc-{n}")
            if job is None:
                return
            with lock:
                claimed.append(job.job_id)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        ours = [c for c in claimed if c in ids]
        assert sorted(ours) == sorted(ids)  # each exactly once, none lost
    finally:
        for job_id in ids:
            _delete(job_id)


def test_hostile_inputs_are_rejected_cleanly(client):
    # Wrong types and out-of-range values -> 422 envelope, never a 500.
    bad_robot = client.post("/api/robots", json={"brand": 42, "model": [], "body_radius_m": "big"})
    assert bad_robot.status_code == 422
    assert bad_robot.json()["error"]["code"] == "VALIDATION_ERROR"

    huge_frames = {
        "format": "json",
        "content": "["
        + ",".join(
            f'{{"t_s": {i}.0, "x_m": 0, "y_m": 0, "min_obstacle_distance_m": 1.0}}'
            for i in range(20001)
        )
        + "]",
    }
    too_many = client.post("/api/imports/telemetry", json=huge_frames)
    assert too_many.status_code == 422

    traversal = client.post("/api/robots/../../etc/apply-to-scenario", json={})
    assert traversal.status_code in (404, 405)

    bad_policy = client.post(
        "/api/runs",
        json={
            "scenario": client.get("/api/scenarios/reference").json()[0],
            "policy": {"max_speed_mps": 999},
        },
    )
    assert bad_policy.status_code == 422


def test_unhandled_exception_returns_envelope_not_stack(temp_workspace):
    from fastapi.testclient import TestClient
    from app.main import create_app

    app = create_app()

    @app.get("/api/_boom_hardening_test")
    def _boom():
        raise RuntimeError("kaboom-secret-detail")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        res = test_client.get("/api/_boom_hardening_test")
    assert res.status_code == 500
    body = res.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "kaboom" not in res.text  # no leaked internals
