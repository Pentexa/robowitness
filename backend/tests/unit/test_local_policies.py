"""İş 3B local policy tests: gate, adapter, subprocess isolation, full run."""

import time

import pytest
from app.config import settings
from app.jobs.repository import claim_next_job
from app.jobs.service import JobExecutionService
from app.policies.local_adapter import LocalPolicyError, SubprocessPolicy
from app.schemas.policy import PolicyConfig, SensorObservation


def _obs() -> SensorObservation:
    return SensorObservation(
        sample_tick=0,
        delivered_tick=0,
        age_s=0.0,
        valid=True,
        observed_pose={"yaw_rad": 0.0},
        goal_rel_x_m=5.0,
        goal_rel_y_m=0.0,
        goal_distance_m=5.0,
        obstacles=[],
    )


@pytest.fixture
def enable_local_policy():
    previous = settings.RW_ALLOW_LOCAL_POLICY
    settings.RW_ALLOW_LOCAL_POLICY = "on"
    yield
    settings.RW_ALLOW_LOCAL_POLICY = previous


def test_gate_off_by_default_returns_403(client):
    assert settings.local_policy_enabled is False
    ref = client.get("/api/scenarios/reference").json()[0]
    res = client.post(
        "/api/runs",
        json={"scenario": ref, "policy": {}, "local_policy": "example_policy"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "LOCAL_POLICY_DISABLED"


def test_list_local_policies_shows_example_and_gate_state(client):
    res = client.get("/api/local-policies")
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is False
    names = {p["name"] for p in body["policies"]}
    assert "example_policy" in names


def test_adapter_drives_and_clamps_commands():
    with SubprocessPolicy("example_policy") as plugin:
        cmd = plugin(_obs(), PolicyConfig())
    assert -0.5 <= cmd.linear_mps <= 1.5
    assert cmd.linear_mps > 0  # goal straight ahead -> moves forward


def test_adapter_missing_and_traversal_names_rejected():
    with pytest.raises(LocalPolicyError):
        SubprocessPolicy("yok_boyle")
    with pytest.raises(LocalPolicyError):
        SubprocessPolicy("../worker")


def test_plugin_error_surfaces_as_local_policy_error(tmp_path):
    from app.policies import local_adapter

    bad = local_adapter.LOCAL_POLICY_DIR / "tmp_bad_policy.py"
    bad.write_text("def policy(o, c):\n    raise ValueError('boom')\n", encoding="utf-8")
    try:
        with SubprocessPolicy("tmp_bad_policy") as plugin:
            with pytest.raises(LocalPolicyError):
                plugin(_obs(), PolicyConfig())
    finally:
        bad.unlink(missing_ok=True)


def test_full_run_with_local_policy_reaches_goal(client, enable_local_policy):
    lib = client.get("/api/scenarios/library").json()
    scenario = next(e["scenario"] for e in lib if e["scenario"]["id"] == "RW-LIB-009")
    res = client.post(
        "/api/runs",
        json={"scenario": scenario, "policy": {}, "local_policy": "example_policy"},
    )
    assert res.status_code == 202, res.text
    deadline = time.time() + 30
    run_id = res.json()["result_id"]
    while time.time() < deadline:
        job = claim_next_job("test-local-policy")
        if job is not None:
            JobExecutionService().execute_simulation_run(job)
            break
        time.sleep(0.1)
    run = client.get(f"/api/runs/{run_id}")
    assert run.status_code == 200, run.text
    assert run.json()["oracle_status"] == "PASS"
    assert run.json()["metrics"]["goal_reached"] is True
