"""Enterprise tests: API keys/RBAC, workspace isolation, audit, metrics, maps, CI gate."""

import pytest
from app.config import settings
from app.schemas.battery import BatteryEntry, BatteryResult, summarize
from app.schemas.telemetry import RunMetrics
from app.verification.battery_gate import evaluate_battery_gate

ROBOT = {
    "brand": "WsBot",
    "model": "WS-1",
    "drive_type": "differential_drive",
    "body_radius_m": 0.25,
    "sensor_type": "2D LiDAR",
    "sensor_range_m": 4.0,
    "sensor_latency_ms": 0,
    "sensor_noise_std_m": 0.0,
}


@pytest.fixture
def api_keys():
    previous = settings.RW_API_KEYS
    settings.RW_API_KEYS = "admin-key:admin:ws-a;viewer-key:viewer:ws-a;editor-key:editor:ws-b"
    yield
    settings.RW_API_KEYS = previous


def test_auth_required_and_viewer_cannot_write(client, api_keys):
    assert client.get("/api/robots").status_code == 401
    assert client.get("/api/health").status_code == 200  # health stays public
    viewer = {"X-API-Key": "viewer-key"}
    assert client.get("/api/robots", headers=viewer).status_code == 200
    denied = client.post("/api/robots", headers=viewer, json=ROBOT)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN_ROLE"
    bad = client.get("/api/robots", headers={"X-API-Key": "yanlis"})
    assert bad.status_code == 401


def test_workspace_isolation_for_robots(client):
    created = client.post("/api/robots", json=ROBOT, headers={"X-Workspace-Id": "ws-iso-a"})
    assert created.status_code == 201, created.text
    rid = created.json()["robot_id"]
    try:
        in_a = client.get("/api/robots", headers={"X-Workspace-Id": "ws-iso-a"}).json()
        in_b = client.get("/api/robots", headers={"X-Workspace-Id": "ws-iso-b"}).json()
        assert any(r["robot_id"] == rid for r in in_a)
        assert not any(r["robot_id"] == rid for r in in_b)
        # Builtin robots are shared across workspaces.
        assert any(r["robot_id"] == "robot-jackal" for r in in_b)
        # Cross-workspace access to the user robot is a 404, not a leak.
        assert (
            client.get(f"/api/robots/{rid}", headers={"X-Workspace-Id": "ws-iso-b"}).status_code
            == 404
        )
    finally:
        client.delete(f"/api/robots/{rid}", headers={"X-Workspace-Id": "ws-iso-a"})


def test_audit_trail_records_writes_and_metrics_respond(client):
    created = client.post(
        "/api/policy-profiles",
        json={
            "name": "Audit Profili",
            "description": "",
            "policy": {"id": "candidate-audit"},
        },
    )
    assert created.status_code == 201
    pid = created.json()["profile_id"]
    try:
        audit = client.get("/api/audit?limit=20")
        assert audit.status_code == 200
        paths = [e["path"] for e in audit.json()["entries"]]
        assert "/api/policy-profiles" in paths

        metrics = client.get("/api/metrics")
        assert metrics.status_code == 200
        body = metrics.json()
        assert body["workspace_id"] == "default"
        assert body["policy_profiles_user"] >= 1
        assert "jobs_by_status" in body
    finally:
        client.delete(f"/api/policy-profiles/{pid}")


def test_audit_requires_admin_when_keys_on(client, api_keys):
    viewer = client.get("/api/audit", headers={"X-API-Key": "viewer-key"})
    assert viewer.status_code == 403


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


def test_map_conversion_produces_valid_scenario(client):
    res = client.post(
        "/api/maps/scenario",
        json={"name": "Salon", "grid_text": MAP_GRID, "cell_size_m": 0.5},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    scenario = body["scenario"]
    assert scenario["id"].startswith("RW-MAP-")
    assert scenario["world"]["width_m"] == 12.0
    assert len(scenario["obstacles"]) == 1  # one connected wall cluster
    assert scenario["robot"]["start"]["x_m"] < 2.0  # S marker honored


def test_map_too_small_rejected_422(client):
    res = client.post(
        "/api/maps/scenario",
        json={"name": "Kucuk", "grid_text": "....\n.SG.\n....", "cell_size_m": 0.5},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "MAP_CONVERSION_FAILED"


def _battery(passed: int, total: int, collisions: int, near: int) -> BatteryResult:
    entries = []
    fail_idx = 0
    for i in range(total):
        ok = i < passed
        is_collision = (not ok) and fail_idx < collisions
        is_near = (not ok) and (not is_collision) and (fail_idx - collisions) < near
        if not ok:
            fail_idx += 1
        entries.append(
            BatteryEntry(
                scenario_id=f"S{i}",
                run_id=f"run-{i}",
                oracle_status="PASS" if ok else "FAIL",
                reason_codes=[] if ok else ["MIN_CLEARANCE_VIOLATION"],
                metrics=RunMetrics(
                    total_ticks=10,
                    sim_duration_s=1.0,
                    min_clearance_m=0.5 if ok else 0.1,
                    goal_reached=True,
                    collision_detected=is_collision,
                    stuck_detected=False,
                    timeout_detected=False,
                ),
                near_miss=is_near,
            )
        )
    return BatteryResult(
        battery_id="battery-x",
        robot_id="r",
        robot_label="R",
        policy_id="p",
        entries=entries,
        summary=summarize(entries),
        created_at="2026-01-01T00:00:00+00:00",
    )


def test_battery_gate_thresholds():
    good = _battery(9, 10, 0, 1)
    assert evaluate_battery_gate(good, min_pass_rate=0.8, max_collisions=0)["passed"] is True
    assert evaluate_battery_gate(good, min_pass_rate=1.0)["passed"] is False
    bad = _battery(9, 10, 1, 0)  # one failed entry, and it is a collision
    assert evaluate_battery_gate(bad, min_pass_rate=0.8, max_collisions=0)["passed"] is False
    assert evaluate_battery_gate(bad, min_pass_rate=0.8, max_collisions=1)["passed"] is True
