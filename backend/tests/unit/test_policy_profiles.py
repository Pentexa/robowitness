"""Policy profile tests: seeds, CRUD, duplicate/builtin guards."""

USER_PROFILE = {
    "name": "Test Profili",
    "description": "pytest profili",
    "policy": {
        "id": "candidate-test",
        "max_speed_mps": 0.5,
        "safe_distance_m": 0.9,
        "reaction_margin_m": 0.2,
        "brake_gain": 3.5,
        "obstacle_prediction_horizon_s": 0.8,
    },
}


def test_builtin_profiles_seeded(client):
    res = client.get("/api/policy-profiles")
    assert res.status_code == 200
    profiles = res.json()
    assert len(profiles) >= 4
    assert all(p["source"] == "builtin" for p in profiles)
    ids = {p["profile_id"] for p in profiles}
    assert {"profile-baseline", "profile-balanced", "profile-cautious", "profile-fast"} <= ids


def test_create_update_delete_user_profile(client):
    created = client.post("/api/policy-profiles", json=USER_PROFILE)
    assert created.status_code == 201, created.text
    pid = created.json()["profile_id"]
    try:
        dup = client.post("/api/policy-profiles", json={**USER_PROFILE, "name": "test profili"})
        assert dup.status_code == 409

        updated = client.put(
            f"/api/policy-profiles/{pid}",
            json={**USER_PROFILE, "policy": {**USER_PROFILE["policy"], "max_speed_mps": 0.4}},
        )
        assert updated.status_code == 200
        assert updated.json()["policy"]["max_speed_mps"] == 0.4
    finally:
        assert client.delete(f"/api/policy-profiles/{pid}").status_code == 200
    assert client.get(f"/api/policy-profiles/{pid}").status_code == 404


def test_builtin_profile_readonly_and_unknown_404(client):
    assert client.put("/api/policy-profiles/profile-balanced", json=USER_PROFILE).status_code == 403
    assert client.delete("/api/policy-profiles/profile-balanced").status_code == 403
    assert client.get("/api/policy-profiles/profile-yok").status_code == 404


def test_invalid_policy_rejected_422(client):
    bad = {**USER_PROFILE, "policy": {**USER_PROFILE["policy"], "max_speed_mps": 99}}
    assert client.post("/api/policy-profiles", json=bad).status_code == 422
