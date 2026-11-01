"""Robot catalog tests: seeds, CRUD, duplicate/builtin guards, apply-to-scenario."""

USER_ROBOT = {
    "brand": "TestBotics",
    "model": "TB-Unit 2000",
    "variant": "Lab",
    "year": 2025,
    "drive_type": "differential_drive",
    "body_radius_m": 0.28,
    "wheel_base_m": 0.5,
    "wheel_radius_m": 0.1,
    "weight_kg": 12.5,
    "max_speed_mps": 1.2,
    "max_payload_kg": 5.0,
    "sensor_type": "2D LiDAR",
    "sensor_range_m": 6.0,
    "sensor_latency_ms": 120,
    "sensor_noise_std_m": 0.02,
    "compute_unit": "Unit-test PC",
    "operating_system": "ROS 2",
    "battery_wh": 500.0,
    "notes": "pytest ile eklenen test robotu",
}


def _scenario(client):
    return client.get("/api/scenarios/reference").json()[0]


def test_builtin_catalog_seeded_with_honest_compatibility(client):
    res = client.get("/api/robots")
    assert res.status_code == 200
    robots = res.json()
    assert len(robots) >= 6
    assert all(r["source"] == "builtin" for r in robots)
    by_id = {r["robot_id"]: r for r in robots}
    assert by_id["robot-turtlebot3-waffle-pi"]["simulation_compatible"] is True
    assert by_id["robot-spot"]["simulation_compatible"] is False
    assert "DRIVE_TYPE_NOT_DIFFERENTIAL_DRIVE" in by_id["robot-spot"]["compatibility_issues"]
    assert by_id["robot-mir250"]["simulation_compatible"] is False
    assert "BODY_RADIUS_OUT_OF_SIM_RANGE" in by_id["robot-mir250"]["compatibility_issues"]


def test_create_get_update_delete_user_robot(client):
    created = client.post("/api/robots", json=USER_ROBOT)
    assert created.status_code == 201, created.text
    robot = created.json()
    assert robot["source"] == "user"
    assert robot["simulation_compatible"] is True
    assert robot["brand"] == "TestBotics"

    fetched = client.get(f"/api/robots/{robot['robot_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["model"] == "TB-Unit 2000"

    updated = client.put(
        f"/api/robots/{robot['robot_id']}", json={**USER_ROBOT, "sensor_latency_ms": 300}
    )
    assert updated.status_code == 200
    assert updated.json()["sensor_latency_ms"] == 300

    deleted = client.delete(f"/api/robots/{robot['robot_id']}")
    assert deleted.status_code == 200
    assert client.get(f"/api/robots/{robot['robot_id']}").status_code == 404


def test_duplicate_brand_model_variant_rejected(client):
    first = client.post("/api/robots", json=USER_ROBOT)
    assert first.status_code == 201
    try:
        dup = client.post("/api/robots", json={**USER_ROBOT, "brand": "testbotics"})
        assert dup.status_code == 409
        assert dup.json()["error"]["code"] == "ROBOT_ALREADY_EXISTS"
    finally:
        client.delete(f"/api/robots/{first.json()['robot_id']}")


def test_builtin_robot_cannot_be_edited_or_deleted(client):
    put = client.put("/api/robots/robot-jackal", json=USER_ROBOT)
    assert put.status_code == 403
    delete = client.delete("/api/robots/robot-jackal")
    assert delete.status_code == 403


def test_unknown_robot_404_and_validation_422(client):
    assert client.get("/api/robots/robot-yok").status_code == 404
    bad = client.post("/api/robots", json={**USER_ROBOT, "body_radius_m": 5.0})
    assert bad.status_code == 422


def test_apply_robot_to_scenario_maps_only_physical_fields(client):
    created = client.post("/api/robots", json=USER_ROBOT).json()
    try:
        scenario = _scenario(client)
        res = client.post(f"/api/robots/{created['robot_id']}/apply-to-scenario", json=scenario)
        assert res.status_code == 200, res.text
        applied = res.json()
        assert applied["robot"]["body_radius_m"] == 0.28
        assert applied["robot"]["wheel_base_m"] == 0.5
        assert applied["robot"]["sensor_range_m"] == 6.0
        assert applied["robot"]["sensor_latency_ms"] == 120
        assert applied["robot"]["sensor_noise_std_m"] == 0.02
        # Scenario-owned fields stay untouched.
        assert applied["robot"]["start"] == scenario["robot"]["start"]
        assert applied["robot"]["goal"] == scenario["robot"]["goal"]
        assert applied["id"] == scenario["id"]
    finally:
        client.delete(f"/api/robots/{created['robot_id']}")


def test_apply_incompatible_robot_rejected_422(client):
    scenario = _scenario(client)
    res = client.post("/api/robots/robot-spot/apply-to-scenario", json=scenario)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "ROBOT_NOT_SIM_COMPATIBLE"
