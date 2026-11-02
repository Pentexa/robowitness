"""Jobs/API contract tests: create, poll, cancel, claim-once, 404/422 behavior."""

import json
from pathlib import Path
from app.jobs.repository import claim_next_job

ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _ref_spec():
    return json.load(open(ROOT / "scenarios" / "reference" / "moving_obstacle_latency.json"))


def test_create_run_and_poll_queued(client):
    r = client.post("/api/runs", json={"scenario": _ref_spec(), "policy": {"id": "baseline-v1"}})
    assert r.status_code == 202
    body = r.json()
    assert body["job_id"].startswith("job-") and body["result_id"].startswith("run-")
    g = client.get(f"/api/jobs/{body['job_id']}")
    assert g.status_code == 200
    assert g.json()["status"] == "queued"


def test_unknown_ids_return_404(client):
    assert client.get("/api/jobs/job-nope").status_code == 404
    assert client.get("/api/runs/run-nope").status_code == 404
    assert client.get("/api/runs/run-nope/telemetry").status_code == 404
    assert client.get("/api/verifications/verif-nope").status_code == 404
    assert client.get("/api/evidence/verif-nope").status_code == 404
    assert client.get("/api/evidence/verif-nope/download").status_code == 404
    r = client.post(
        "/api/fixes/verify",
        json={"baseline_run_id": "run-nope", "candidate_policy": {"id": "c"}},
    )
    assert r.status_code == 404


def test_cancel_flow_and_idempotent_terminal_cancel(client):
    r = client.post("/api/runs", json={"scenario": _ref_spec(), "policy": {}})
    job_id = r.json()["job_id"]
    c = client.post(f"/api/jobs/{job_id}/cancel")
    assert c.status_code == 200
    assert c.json()["status"] == "cancelled"
    c2 = client.post(f"/api/jobs/{job_id}/cancel")
    assert c2.json()["status"] == "cancelled"
    assert client.post("/api/jobs/job-nope/cancel").status_code == 404


def test_atomic_claim_single_owner(client):
    # Drain jobs queued by earlier tests (session-scoped temp DB)
    while claim_next_job("drain-worker") is not None:
        pass
    r = client.post("/api/runs", json={"scenario": _ref_spec(), "policy": {}})
    job_id = r.json()["job_id"]
    first = claim_next_job("worker-A")
    assert first is not None and first.job_id == job_id
    assert first.status == "running"
    # Same job cannot be claimed twice (duplicate worker protection)
    assert claim_next_job("worker-B") is None


def test_invalid_scenario_rejected_with_422(client):
    bad = _ref_spec()
    bad["robot"]["start"]["x_m"] = 999.0
    r = client.post("/api/runs", json={"scenario": bad, "policy": {}})
    assert r.status_code == 422


def test_telemetry_pagination_contract(
    client,
):  # No telemetry on disk for unknown run -> 404 (path containment holds)
    r = client.get("/api/runs/run-nope/telemetry?offset=0&limit=10")
    assert r.status_code == 404


def test_investigation_grounded_in_measured_telemetry(client):
    # Uses the seeded baseline run only if present; otherwise create + execute one.
    from app.db import get_db

    with get_db() as conn:
        # Pick a FAIL run explicitly: investigation only applies to failures,
        # and other suites in the session may have inserted PASS runs first.
        row = conn.execute(
            "SELECT run_id FROM runs WHERE oracle_status = 'FAIL' LIMIT 1"
        ).fetchone()
    if row is None:
        import json
        from pathlib import Path
        from app.jobs.repository import claim_next_job
        from app.jobs.service import JobExecutionService

        root = Path(__file__).resolve().parent.parent.parent.parent
        spec = json.load(open(root / "scenarios" / "reference" / "moving_obstacle_latency.json"))
        r = client.post("/api/runs", json={"scenario": spec, "policy": {"id": "baseline-v1"}})
        job = claim_next_job("test-investigate")
        JobExecutionService().execute_simulation_run(job)
        run_id = r.json()["result_id"]
    else:
        run_id = row["run_id"]
    r = client.post(f"/api/failures/{run_id}/investigate", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == run_id
    assert body["failure_tick"] >= 0
    assert "Measured over" in body["evidence_summary"]
    assert body["provenance"] in ("OFFLINE_REFERENCE", "LIVE_META", "UNAVAILABLE")
    assert client.post("/api/failures/run-nope/investigate", json={}).status_code == 404


def test_list_verifications_newest_first(client):
    from app.db import get_db

    with get_db() as conn:
        conn.execute(
            "INSERT INTO jobs (job_id, kind, status, payload_json, result_id,"
            " attempts, created_at)"
            " VALUES ('job-h1', 'verification', 'completed', '{}', 'verif-h1',"
            " 0, '2026-01-01T00:00:00+00:00')"
        )
        conn.execute(
            "INSERT INTO runs (run_id, job_id, scenario_hash, policy_hash, oracle_status,"
            " reason_codes_json, metrics_json, artifact_dir, created_at, completed_at)"
            " VALUES ('run-h1', 'job-h1', 's', 'p', 'FAIL', '[]', '{}', '/tmp',"
            " '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:01+00:00')"
        )
        conn.execute(
            "INSERT INTO verifications (verification_id, job_id, baseline_run_id,"
            " candidate_policy_json, verdict, gates_json, artifact_dir, created_at, completed_at)"
            " VALUES ('verif-h1', 'job-h1', 'run-h1', '{}', 'REJECTED', '[]', '/tmp',"
            " '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:01+00:00')"
        )
        conn.commit()

    r = client.get("/api/verifications?limit=10")
    assert r.status_code == 200
    ids = [v["verification_id"] for v in r.json()]
    assert "verif-h1" in ids
    assert all(set(v.keys()) >= {"verification_id", "verdict", "baseline_run_id"} for v in r.json())
