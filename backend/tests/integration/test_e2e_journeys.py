"""End-to-end user journeys: full workflows through API + worker + oracle.

Each test drives the same path a user (or a judge) would: queue via HTTP,
execute via the real job service, read verdicts back via HTTP, and verify
sealed evidence independently. No mocks.
"""

from pathlib import Path

import pytest
from app.config import settings
from app.evidence.integrity import verify_package_integrity
from app.evidence.recorder import VERIFICATION_REQUIRED_FILES
from app.jobs.repository import claim_next_job
from app.jobs.service import JobExecutionService

ROOT = Path(__file__).resolve().parent.parent.parent.parent

BASELINE_POLICY = {
    "id": "baseline-v1",
    "max_speed_mps": 0.75,
    "safe_distance_m": 0.30,
    "reaction_margin_m": 0.05,
    "brake_gain": 1.5,
    "obstacle_prediction_horizon_s": 0.0,
}
OVERCAUTIOUS = {
    "id": "candidate-overcautious-v1",
    "max_speed_mps": 0.05,
    "safe_distance_m": 2.0,
    "reaction_margin_m": 1.0,
    "brake_gain": 10.0,
    "obstacle_prediction_horizon_s": 2.0,
}
CANDIDATE_FINAL = {
    "id": "candidate-final-v1",
    "max_speed_mps": 0.60,
    "safe_distance_m": 1.00,
    "reaction_margin_m": 0.20,
    "brake_gain": 4.0,
    "obstacle_prediction_horizon_s": 1.00,
}


def _execute_until(client_job_id: str) -> None:
    """Claim jobs (oldest first) and execute them until ours is done."""
    service = JobExecutionService()
    for _ in range(50):
        job = claim_next_job("e2e-test")
        assert job is not None, "job queue drained before our job ran"
        if job.kind == "simulation_run":
            service.execute_simulation_run(job)
        elif job.kind == "battery_run":
            service.execute_battery_run(job)
        elif job.kind == "verification":
            service.execute_verification(job)
        if job.job_id == client_job_id:
            return
    raise AssertionError(f"job {client_job_id} never claimed")


def _run_baseline(client, scenario) -> str:
    res = client.post("/api/runs", json={"scenario": scenario, "policy": BASELINE_POLICY})
    assert res.status_code == 202, res.text
    _execute_until(res.json()["job_id"])
    return res.json()["result_id"]


def _reference_scenario(client):
    return client.get("/api/scenarios/reference").json()[0]


# ---------------------------------------------------------------------------
# Journey 1: run -> fail -> investigate -> patch -> verify (rejected) -> sealed
# ---------------------------------------------------------------------------


def test_journey_failure_investigation_rejection_and_sealed_evidence(client):
    scenario = _reference_scenario(client)
    run_id = _run_baseline(client, scenario)

    run = client.get(f"/api/runs/{run_id}")
    assert run.status_code == 200
    body = run.json()
    assert body["oracle_status"] == "FAIL"
    assert body["metrics"]["collision_detected"] is True
    assert "COLLISION" in body["reason_codes"]

    telemetry = client.get(f"/api/runs/{run_id}/telemetry?offset=0&limit=10")
    assert telemetry.status_code == 200 and telemetry.json()["total"] > 300

    investigation = client.post(f"/api/failures/{run_id}/investigate", json={})
    assert investigation.status_code == 200, investigation.text
    inv = investigation.json()
    assert inv["failure_tick"] >= 300  # measured collision neighborhood
    assert inv["suggested_patch"]

    verify = client.post(
        "/api/fixes/verify",
        json={"baseline_run_id": run_id, "candidate_policy": OVERCAUTIOUS},
    )
    assert verify.status_code == 202, verify.text
    _execute_until(verify.json()["job_id"])
    verification_id = verify.json()["result_id"]

    record = client.get(f"/api/verifications/{verification_id}")
    assert record.status_code == 200
    verdict = record.json()
    assert verdict["verdict"] == "REJECTED"
    gates = {g["gate_id"]: g["status"] for g in verdict["gates"]}
    assert gates["GATE_1_REPRODUCE"] == "PASS"
    assert gates["GATE_5_INTEGRITY"] == "PASS"

    evidence = client.get(f"/api/evidence/{verification_id}")
    assert evidence.status_code == 200
    assert "report.md" in evidence.json()["files"]
    download = client.get(f"/api/evidence/{verification_id}/download")
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"

    package_dir = Path(verdict["artifact_dir"])
    ok, errors = verify_package_integrity(package_dir, VERIFICATION_REQUIRED_FILES)
    assert ok, errors


# ---------------------------------------------------------------------------
# Journey 2: custom robot -> battery report card -> comparison -> report file
# ---------------------------------------------------------------------------

USER_ROBOT = {
    "brand": "E2E Robotics",
    "model": "JourneyBot 3000",
    "drive_type": "differential_drive",
    "body_radius_m": 0.28,
    "wheel_base_m": 0.5,
    "wheel_radius_m": 0.1,
    "weight_kg": 12.0,
    "sensor_type": "2D LiDAR",
    "sensor_range_m": 6.0,
    "sensor_latency_ms": 120,
    "sensor_noise_std_m": 0.02,
}


def test_journey_custom_robot_battery_card_compare_and_report(client):
    created = client.post("/api/robots", json=USER_ROBOT)
    assert created.status_code == 201, created.text
    robot_id = created.json()["robot_id"]
    battery_ids = []
    try:
        for _ in range(2):
            battery = client.post(
                "/api/batteries",
                json={
                    "robot_id": robot_id,
                    "scenario_ids": ["RW-LIB-009", "RW-LIB-002"],
                    "policy": BASELINE_POLICY,
                },
            )
            assert battery.status_code == 202, battery.text
            _execute_until(battery.json()["job_id"])
            battery_ids.append(battery.json()["result_id"])

        card = client.get(f"/api/batteries/{battery_ids[0]}")
        assert card.status_code == 200
        body = card.json()
        assert body["summary"]["total"] == 2
        entries = {e["scenario_id"]: e for e in body["entries"]}
        assert entries["RW-LIB-009"]["oracle_status"] == "PASS"
        # Every entry replays through the runs API.
        replay = client.get(f"/api/runs/{entries['RW-LIB-009']['run_id']}")
        assert replay.status_code == 200

        report = client.get(f"/api/batteries/{battery_ids[0]}/report.md")
        assert report.status_code == 200 and "Robot Sınav Karnesi" in report.text

        compared = client.get(f"/api/batteries/compare?a={battery_ids[0]}&b={battery_ids[1]}")
        assert compared.status_code == 200
        outcomes = {e["scenario_id"]: e["outcome"] for e in compared.json()["entries"]}
        assert outcomes["RW-LIB-009"] in ("same", "improved", "worsened")

        trend = client.get("/api/batteries/trend")
        assert trend.status_code == 200 and len(trend.json()) >= 2
    finally:
        client.delete(f"/api/robots/{robot_id}")


# ---------------------------------------------------------------------------
# Journey 3: own map -> scenario -> run; real log -> judgement -> metrics/audit
# ---------------------------------------------------------------------------

MAP_GRID = "\n".join(
    [
        "........................",
        ".S........##............",
        "..........##......G.....",
        "..........##............",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
    ]
)


def test_journey_map_scenario_and_real_log_and_admin_views(client):
    converted = client.post(
        "/api/maps/scenario",
        json={"name": "E2E Salon", "grid_text": MAP_GRID, "cell_size_m": 0.5},
    )
    assert converted.status_code == 200, converted.text
    scenario = converted.json()["scenario"]
    run_id = _run_baseline(client, scenario)
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["oracle_status"] in ("PASS", "FAIL", "INCONCLUSIVE")

    csv_log = (
        "t_s,x_m,y_m,yaw_rad,min_obstacle_distance_m\n"
        "0.0,1.0,4.0,0.0,2.0\n1.0,5.0,4.0,0.0,0.10\n2.0,10.8,4.0,0.0,1.5\n"
    )
    imported = client.post(
        "/api/imports/telemetry",
        json={
            "name": "e2e-drive.csv",
            "robot_label": "JourneyBot 3000",
            "format": "csv",
            "content": csv_log,
            "goal": {"x_m": 11.0, "y_m": 4.0},
        },
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["oracle_status"] == "FAIL"
    assert imported.json()["near_miss"] is True

    metrics = client.get("/api/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["telemetry_imports"] >= 1

    audit = client.get("/api/audit?limit=10")
    assert audit.status_code == 200
    assert any(e["path"] == "/api/imports/telemetry" for e in audit.json()["entries"])


# ---------------------------------------------------------------------------
# Journey 4: enterprise key lifecycle gates the API end-to-end
# ---------------------------------------------------------------------------


def test_journey_api_key_lifecycle_end_to_end(client):
    first = client.post(
        "/api/admin/api-keys",
        json={"label": "e2e-admin", "role": "admin", "workspace_id": "ws-e2e"},
    )
    if first.status_code == 422:
        pytest.skip("an active key already exists in this session; lifecycle covered elsewhere")
    assert first.status_code == 201, first.text
    admin_key = first.json()["api_key"]
    headers = {"X-API-Key": admin_key}
    try:
        assert client.get("/api/robots").status_code == 401  # auth now enforced
        viewer = client.post(
            "/api/admin/api-keys",
            json={"label": "e2e-viewer", "role": "viewer", "workspace_id": "ws-e2e"},
            headers=headers,
        )
        assert viewer.status_code == 201
        viewer_headers = {"X-API-Key": viewer.json()["api_key"]}
        assert client.get("/api/robots", headers=viewer_headers).status_code == 200
        assert (
            client.post("/api/robots", json=USER_ROBOT, headers=viewer_headers).status_code == 403
        )
        client.delete(f"/api/admin/api-keys/{viewer.json()['key_id']}", headers=headers)
    finally:
        client.delete(f"/api/admin/api-keys/{first.json()['key_id']}", headers=headers)
    assert client.get("/api/robots").status_code == 200  # open again


# ---------------------------------------------------------------------------
# Journey 5: the verified configuration (MPC) earns VERIFIED on frozen v6
# ---------------------------------------------------------------------------


def test_journey_mpc_candidate_earns_verified_on_frozen_set(client, monkeypatch):
    monkeypatch.setattr(settings, "RW_CANDIDATE_LAW", "mpc")
    scenario = _reference_scenario(client)
    run_id = _run_baseline(client, scenario)

    verify = client.post(
        "/api/fixes/verify",
        json={"baseline_run_id": run_id, "candidate_policy": CANDIDATE_FINAL},
    )
    assert verify.status_code == 202, verify.text
    _execute_until(verify.json()["job_id"])

    record = client.get(f"/api/verifications/{verify.json()['result_id']}")
    assert record.status_code == 200
    verdict = record.json()
    assert verdict["verdict"] == "VERIFIED_IN_SIMULATION", verdict["gates"]
    gates = {g["gate_id"]: g for g in verdict["gates"]}
    assert gates["GATE_3_HOLDOUT"]["details"]["passed_cases"] == 20
    package_dir = Path(verdict["artifact_dir"])
    ok, errors = verify_package_integrity(package_dir, VERIFICATION_REQUIRED_FILES)
    assert ok, errors
