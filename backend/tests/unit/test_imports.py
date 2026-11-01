"""Real-log import tests: CSV/JSON parsing, oracle rules, ROS format helpers."""

import json

from app.ros_bridge.format import frames_to_import_payload, odom_to_frame, scan_min_distance

CSV_NEAR_MISS = """t_s,x_m,y_m,yaw_rad,min_obstacle_distance_m
0.0,1.0,4.0,0.0,2.0
1.0,5.0,4.0,0.0,0.10
2.0,10.8,4.0,0.0,1.5
"""

CSV_CLEAN = """t_s,x_m,y_m,yaw_rad,min_obstacle_distance_m
0.0,1.0,4.0,0.0,2.0
2.0,10.8,4.0,0.0,1.5
"""


def test_csv_near_miss_judged_fail_without_collision(client):
    res = client.post(
        "/api/imports/telemetry",
        json={
            "name": "Salon sürüşü 1",
            "robot_label": "TurtleBot3 Waffle Pi",
            "format": "csv",
            "content": CSV_NEAR_MISS,
            "goal": {"x_m": 11.0, "y_m": 4.0},
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["provenance"] == "REAL_LOG"
    assert body["oracle_status"] == "FAIL"
    assert body["near_miss"] is True
    assert body["metrics"]["collision_detected"] is False
    assert body["metrics"]["goal_reached"] is True
    assert body["metrics"]["min_clearance_m"] == 0.10
    fetched = client.get(f"/api/imports/{body['import_id']}")
    assert fetched.status_code == 200


def test_csv_clean_run_passes_and_json_collision_fails(client):
    clean = client.post(
        "/api/imports/telemetry",
        json={"format": "csv", "content": CSV_CLEAN, "goal": {"x_m": 11.0, "y_m": 4.0}},
    )
    assert clean.json()["oracle_status"] == "PASS"

    frames = [
        {"t_s": 0.0, "x_m": 0.0, "y_m": 0.0, "min_obstacle_distance_m": 1.0},
        {"t_s": 1.0, "x_m": 1.0, "y_m": 0.0, "min_obstacle_distance_m": 0.0},
    ]
    hit = client.post(
        "/api/imports/telemetry",
        json={"format": "json", "content": json.dumps({"frames": frames})},
    )
    assert hit.json()["oracle_status"] == "FAIL"
    assert "COLLISION" in hit.json()["reason_codes"]


def test_import_without_distance_data_is_inconclusive(client):
    frames = [{"t_s": 0.0, "x_m": 0.0, "y_m": 0.0}, {"t_s": 1.0, "x_m": 1.0, "y_m": 0.0}]
    res = client.post(
        "/api/imports/telemetry",
        json={"format": "json", "content": json.dumps(frames)},
    )
    assert res.status_code == 201
    assert res.json()["oracle_status"] == "INCONCLUSIVE"


def test_import_parse_errors_422(client):
    bad_csv = client.post("/api/imports/telemetry", json={"format": "csv", "content": "a,b\n1,2\n"})
    assert bad_csv.status_code == 422
    bad_order = client.post(
        "/api/imports/telemetry",
        json={
            "format": "json",
            "content": json.dumps(
                [{"t_s": 2.0, "x_m": 0, "y_m": 0}, {"t_s": 1.0, "x_m": 1, "y_m": 0}]
            ),
        },
    )
    assert bad_order.status_code == 422
    assert client.get("/api/imports/import-yok").status_code == 404


def test_ros_format_helpers_without_ros():
    assert scan_min_distance([float("inf"), 0.5, float("nan"), 2.0], 0.05, 10.0) == 0.5
    assert scan_min_distance([float("inf")], 0.05, 10.0) is None
    frame = odom_to_frame({"stamp_s": 3.0, "x_m": 1.0, "y_m": 2.0, "yaw_rad": 0.5}, 0.7)
    assert frame == {
        "t_s": 3.0,
        "x_m": 1.0,
        "y_m": 2.0,
        "yaw_rad": 0.5,
        "min_obstacle_distance_m": 0.7,
    }
    payload = frames_to_import_payload([frame], "ROS sürüşü", "Jackal")
    assert payload["format"] == "json"
    assert json.loads(payload["content"])["frames"][0]["x_m"] == 1.0
