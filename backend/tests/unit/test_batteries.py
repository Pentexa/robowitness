"""Battery tests: robot gate, scenario resolution, execution, report card."""

from app.jobs.repository import claim_next_job
from app.jobs.service import JobExecutionService

POLICY = {
    "id": "baseline-v1",
    "max_speed_mps": 0.75,
    "safe_distance_m": 0.3,
    "reaction_margin_m": 0.05,
    "brake_gain": 1.5,
    "obstacle_prediction_horizon_s": 0.0,
}


def _run_battery(client, robot_id="robot-turtlebot3-waffle-pi", scenario_ids=None):
    body = {"robot_id": robot_id, "policy": POLICY}
    if scenario_ids is not None:
        body["scenario_ids"] = scenario_ids
    res = client.post("/api/batteries", json=body)
    assert res.status_code == 202, res.text
    job = claim_next_job("test-battery")
    JobExecutionService().execute_battery_run(job)
    return res.json()["result_id"]


def test_incompatible_robot_rejected_422(client):
    res = client.post("/api/batteries", json={"robot_id": "robot-spot", "policy": POLICY})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "ROBOT_NOT_SIM_COMPATIBLE"


def test_unknown_robot_and_scenario_rejected(client):
    assert (
        client.post("/api/batteries", json={"robot_id": "robot-yok", "policy": POLICY}).status_code
        == 404
    )
    res = client.post(
        "/api/batteries",
        json={"robot_id": "robot-jackal", "policy": POLICY, "scenario_ids": ["RW-XXX-999"]},
    )
    assert res.status_code == 422


def test_battery_executes_and_summary_matches_measured_outcomes(client):
    battery_id = _run_battery(client, scenario_ids=["RW-LIB-009", "RW-LIB-001", "RW-LIB-002"])
    res = client.get(f"/api/batteries/{battery_id}")
    assert res.status_code == 200, res.text
    card = res.json()
    assert card["robot_id"] == "robot-turtlebot3-waffle-pi"
    assert card["summary"]["total"] == 3
    by_id = {e["scenario_id"]: e for e in card["entries"]}
    # Measured baseline outcomes (see scenarios/library measurement notes).
    assert by_id["RW-LIB-009"]["oracle_status"] == "PASS"
    assert by_id["RW-LIB-001"]["oracle_status"] == "PASS"
    lib002 = by_id["RW-LIB-002"]
    assert lib002["oracle_status"] == "FAIL"
    assert lib002["near_miss"] is True
    assert lib002["metrics"]["collision_detected"] is False
    assert card["summary"]["passed"] == 2
    assert card["summary"]["near_misses"] == 1
    assert card["summary"]["collisions"] == 0
    # Each entry traces to a real persisted run (replay must work).
    for entry in card["entries"]:
        run = client.get(f"/api/runs/{entry['run_id']}")
        assert run.status_code == 200
        assert run.json()["oracle_status"] == entry["oracle_status"]


def test_battery_report_markdown_download(client):
    battery_id = _run_battery(client, scenario_ids=["RW-LIB-009"])
    res = client.get(f"/api/batteries/{battery_id}/report.md")
    assert res.status_code == 200
    assert "Robot Sınav Karnesi" in res.text
    assert "RW-LIB-009" in res.text
    assert client.get("/api/batteries/battery-yok").status_code == 404


def test_battery_report_english_download(client):
    battery_id = _run_battery(client, scenario_ids=["RW-LIB-009"])
    res = client.get(f"/api/batteries/{battery_id}/report.md?lang=en")
    assert res.status_code == 200
    assert "Robot Exam Report Card" in res.text
    assert "## Summary" in res.text
