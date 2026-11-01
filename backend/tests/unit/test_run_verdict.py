"""Oracle verdict plumbing: PASS runs are refused by failure investigation."""

import json

from app.config import settings
from app.db import get_db


def _seed_run(run_id: str, oracle_status: str, collision: bool) -> None:
    run_dir = settings.artifacts_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    frame = {
        "tick": 0,
        "clearance_m": 0.5,
        "events": [{"type": "COLLISION", "tick": 0}] if collision else [],
    }
    (run_dir / "telemetry.jsonl").write_text(json.dumps(frame) + "\n", encoding="utf-8")
    (run_dir / "metrics.json").write_text(
        json.dumps({"goal_reached": not collision, "collision_detected": collision}),
        encoding="utf-8",
    )
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, job_id, scenario_hash, policy_hash, "
            "oracle_status, reason_codes_json, metrics_json, artifact_dir, created_at) "
            "VALUES (?, NULL, 'h', 'p', ?, '[]', '{}', ?, '2026-01-01T00:00:00+00:00')",
            (run_id, oracle_status, str(run_dir)),
        )
        conn.commit()


def _cleanup(run_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        conn.commit()


def test_pass_run_cannot_be_investigated(client):
    _seed_run("run-test-pass", "PASS", collision=False)
    try:
        res = client.post("/api/failures/run-test-pass/investigate", json={})
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "RUN_DID_NOT_FAIL"
    finally:
        _cleanup("run-test-pass")


def test_inconclusive_run_cannot_be_investigated(client):
    _seed_run("run-test-inc", "INCONCLUSIVE", collision=False)
    try:
        res = client.post("/api/failures/run-test-inc/investigate", json={})
        assert res.status_code == 409
    finally:
        _cleanup("run-test-inc")


def test_fail_run_can_be_investigated(client):
    _seed_run("run-test-fail", "FAIL", collision=True)
    try:
        res = client.post("/api/failures/run-test-fail/investigate", json={})
        assert res.status_code == 200
        assert res.json()["failure_tick"] == 0
    finally:
        _cleanup("run-test-fail")
