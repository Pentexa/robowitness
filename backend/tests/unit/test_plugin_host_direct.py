"""Direct plugin-host protocol tests (the subprocess coverage cannot see)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from app.policies.local.example_policy import policy as example_policy_fn

BACKEND = Path(__file__).resolve().parent.parent.parent


def _run_host(policy_file: Path, lines: list[str]) -> list[dict]:
    proc = subprocess.run(
        [sys.executable, "-m", "app.policies.plugin_host", str(policy_file)],
        input="\n".join(lines),
        capture_output=True,
        text=True,
        cwd=str(BACKEND),
        timeout=30,
    )
    return [json.loads(line) for line in proc.stdout.strip().splitlines() if line.strip()]


def test_example_policy_direct_calls():
    ahead = {
        "goal_rel_x_m": 5.0,
        "goal_rel_y_m": 0.0,
        "obstacles": [],
    }
    config = {
        "max_speed_mps": 0.6,
        "safe_distance_m": 1.0,
        "reaction_margin_m": 0.2,
        "brake_gain": 4.0,
        "obstacle_prediction_horizon_s": 1.0,
    }
    cmd = example_policy_fn(ahead, config)
    assert cmd["linear_mps"] == pytest.approx(0.6)

    near = {
        "goal_rel_x_m": 5.0,
        "goal_rel_y_m": 0.0,
        "obstacles": [
            {"id": "O1", "rel_x_m": 1.0, "rel_y_m": 0.1, "radius_m": 0.3, "distance_m": 0.5}
        ],
    }
    slowed = example_policy_fn(near, config)
    assert slowed["linear_mps"] < cmd["linear_mps"]


def test_plugin_host_answers_json_lines():
    policy_file = BACKEND / "app" / "policies" / "local" / "example_policy.py"
    request = json.dumps(
        {
            "observation": {
                "goal_rel_x_m": 5.0,
                "goal_rel_y_m": 0.0,
                "obstacles": [],
            },
            "config": {
                "max_speed_mps": 0.6,
                "safe_distance_m": 1.0,
                "reaction_margin_m": 0.2,
                "brake_gain": 4.0,
                "obstacle_prediction_horizon_s": 1.0,
            },
        }
    )
    responses = _run_host(policy_file, [request])
    assert len(responses) == 1
    assert responses[0]["linear_mps"] == pytest.approx(0.6)


def test_plugin_host_reports_policy_errors(tmp_path):
    bad = tmp_path / "bad_policy.py"
    bad.write_text("def policy(o, c):\n    raise ValueError('boom')\n", encoding="utf-8")
    request = json.dumps({"observation": {}, "config": {}})
    responses = _run_host(bad, [request])
    assert "error" in responses[0]
    assert "POLICY_ERROR" in responses[0]["error"]


def test_plugin_host_missing_callable_fails_fast(tmp_path):
    bad = tmp_path / "no_policy.py"
    bad.write_text("X = 1\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "app.policies.plugin_host", str(bad)],
        input="",
        capture_output=True,
        text=True,
        cwd=str(BACKEND),
        timeout=30,
    )
    assert proc.returncode == 2
    assert "LOAD_FAILED" in proc.stdout
