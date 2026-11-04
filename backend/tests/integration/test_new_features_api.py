"""Integration journeys for the five-feature round (stress, adversarial,
evidence inspection, portable HTML report). Real jobs, real oracle."""

import base64
import io
import json
import zipfile

from app.config import settings
from app.jobs.repository import claim_next_job
from app.jobs.service import JobExecutionService

BASELINE_POLICY = {
    "id": "baseline-v1",
    "max_speed_mps": 0.75,
    "safe_distance_m": 0.30,
    "reaction_margin_m": 0.05,
    "brake_gain": 1.5,
    "obstacle_prediction_horizon_s": 0.0,
}


def _execute_until(client_job_id: str) -> None:
    service = JobExecutionService()
    for _ in range(80):
        job = claim_next_job("feature-test")
        assert job is not None, "job queue drained before our job ran"
        if job.kind == "simulation_run":
            service.execute_simulation_run(job)
        elif job.kind == "battery_run":
            service.execute_battery_run(job)
        elif job.kind == "verification":
            service.execute_verification(job)
        elif job.kind == "stress_test":
            service.execute_stress_test(job)
        elif job.kind == "adversarial_test":
            service.execute_adversarial_test(job)
        if job.job_id == client_job_id:
            return
    raise AssertionError(f"job {client_job_id} never claimed")


def _reference_scenario(client):
    return client.get("/api/scenarios/reference").json()[0]


# --------------------------------------------------------------------- stress


def test_stress_test_grid_runs_and_reports_cells(client):
    scenario = _reference_scenario(client)
    res = client.post(
        "/api/stress-tests",
        json={
            "scenario": scenario,
            "policy": BASELINE_POLICY,
            "latencies_ms": [0, 450],
            "noise_levels_m": [0.0, 0.05],
        },
    )
    assert res.status_code == 202, res.text
    _execute_until(res.json()["job_id"])

    result = client.get(f"/api/stress-tests/{res.json()['result_id']}")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["summary"]["total"] == 4
    assert len(body["cells"]) == 4
    grid = {(c["latency_ms"], c["noise_std_m"]) for c in body["cells"]}
    assert grid == {(0, 0.0), (0, 0.05), (450, 0.0), (450, 0.05)}
    for cell in body["cells"]:
        assert cell["run_id"].startswith("run-")
        assert cell["oracle_status"] in ("PASS", "FAIL", "INCONCLUSIVE")
        run = client.get(f"/api/runs/{cell['run_id']}")
        assert run.status_code == 200  # every cell is a real recorded run


def test_stress_test_rejects_oversized_grid(client):
    scenario = _reference_scenario(client)
    res = client.post(
        "/api/stress-tests",
        json={
            "scenario": scenario,
            "policy": BASELINE_POLICY,
            "latencies_ms": [0, 100, 200, 300, 400, 500, 600, 700],
            "noise_levels_m": [0.0, 0.02, 0.04, 0.06, 0.08, 0.1],
        },
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "STRESS_GRID_TOO_LARGE"


# ---------------------------------------------------------------- adversarial


def test_adversarial_offline_rounds_are_oracle_judged(client):
    res = client.post(
        "/api/adversarial-tests",
        json={"policy": BASELINE_POLICY, "max_iterations": 3},
    )
    assert res.status_code == 202, res.text
    _execute_until(res.json()["job_id"])

    result = client.get(f"/api/adversarial-tests/{res.json()['result_id']}")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["max_iterations"] == 3
    assert len(body["rounds"]) == 3
    # Offline adapter returns the same reference scenario every time:
    # round 1 executes for real, later rounds must not be re-run.
    assert body["executed_count"] == 1
    assert body["rounds"][0]["executed"] is True
    assert body["rounds"][0]["provenance"] == "OFFLINE_REFERENCE"
    assert body["rounds"][0]["oracle_status"] in ("PASS", "FAIL", "INCONCLUSIVE")
    assert body["rounds"][1]["note"] == "duplicate_scenario_not_rerun"
    assert body["stopped_reason"] == "iteration_limit"


# ------------------------------------------------------- evidence inspection


def _run_and_zip(client) -> tuple[str, bytes]:
    scenario = _reference_scenario(client)
    res = client.post("/api/runs", json={"scenario": scenario, "policy": BASELINE_POLICY})
    assert res.status_code == 202, res.text
    _execute_until(res.json()["job_id"])
    run_id = res.json()["result_id"]
    run_dir = settings.artifacts_path / "runs" / run_id
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(run_dir.glob("*")):
            if path.is_file():
                zf.write(path, arcname=path.name)
    return run_id, buffer.getvalue()


def test_evidence_inspect_accepts_real_run_package(client):
    run_id, payload = _run_and_zip(client)
    res = client.post(
        "/api/evidence/inspect",
        json={"filename": "evidence.zip", "content_base64": base64.b64encode(payload).decode()},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True, body
    assert body["package_type"] == "run"
    assert body["package_id"] == run_id


def test_evidence_inspect_detects_tampered_package(client):
    _, payload = _run_and_zip(client)
    # Rebuild the zip with a tampered metrics.json.
    source = zipfile.ZipFile(io.BytesIO(payload))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in source.namelist():
            data = source.read(name)
            if name == "metrics.json":
                data = b'{"total_ticks": 1}'
            zf.writestr(name, data)
    res = client.post(
        "/api/evidence/inspect",
        json={
            "filename": "tampered.zip",
            "content_base64": base64.b64encode(buffer.getvalue()).decode(),
        },
    )
    body = res.json()
    assert body["ok"] is False
    assert any(f["status"] == "MISMATCH" for f in body["files"])


def test_evidence_inspect_rejects_bad_base64(client):
    res = client.post("/api/evidence/inspect", json={"filename": "x.zip", "content_base64": "!!!"})
    assert res.status_code == 422


# ------------------------------------------------------------ portable report


def test_portable_html_report_for_recorded_verification(client):
    """Produce a real verification, then download its standalone HTML."""
    scenario = _reference_scenario(client)
    run_res = client.post("/api/runs", json={"scenario": scenario, "policy": BASELINE_POLICY})
    assert run_res.status_code == 202, run_res.text
    _execute_until(run_res.json()["job_id"])
    baseline_run_id = run_res.json()["result_id"]

    candidate = dict(BASELINE_POLICY, id="candidate-html", max_speed_mps=0.45)
    ver_res = client.post(
        "/api/fixes/verify",
        json={"baseline_run_id": baseline_run_id, "candidate_policy": candidate},
    )
    assert ver_res.status_code == 202, ver_res.text
    _execute_until(ver_res.json()["job_id"])
    verification_id = ver_res.json()["result_id"]

    res = client.get(f"/api/verifications/{verification_id}/report.html")
    assert res.status_code == 200, res.text
    doc = res.text
    assert "RoboWitness" in doc
    assert verification_id in doc
    assert "GATE_1_REPRODUCE" in doc
    assert "<svg" in doc  # sealed telemetry chart
    assert "http://" not in doc and "https://" not in doc  # fully standalone

    record = client.get(f"/api/verifications/{verification_id}").json()
    assert record["verdict"] in doc

    missing = client.get("/api/verifications/verif-nope/report.html")
    assert missing.status_code == 404


def test_inspect_verification_package_type(client):
    """The champion-style verification package inspects as type=verification."""
    scenario = _reference_scenario(client)
    run_res = client.post("/api/runs", json={"scenario": scenario, "policy": BASELINE_POLICY})
    _execute_until(run_res.json()["job_id"])
    ver_res = client.post(
        "/api/fixes/verify",
        json={
            "baseline_run_id": run_res.json()["result_id"],
            "candidate_policy": dict(BASELINE_POLICY, id="candidate-insp"),
        },
    )
    _execute_until(ver_res.json()["job_id"])
    verification_id = ver_res.json()["result_id"]

    download = client.get(f"/api/evidence/{verification_id}/download")
    assert download.status_code == 200
    res = client.post(
        "/api/evidence/inspect",
        json={
            "filename": "evidence.zip",
            "content_base64": base64.b64encode(download.content).decode(),
        },
    )
    body = res.json()
    assert body["ok"] is True, body
    assert body["package_type"] == "verification"
    assert body["package_id"] == verification_id
    assert json.dumps(body)  # serializable report
