"""Unit tests for ScenarioSpec, PolicyConfig, and schema validation."""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.schemas.policy import PolicyConfig, PolicyPatch
from app.schemas.scenario import (
    ObstacleSpec,
    OracleSpec,
    Point2D,
    Pose2D,
    RobotSpec,
    ScenarioSpec,
    WorldSpec,
)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent


def test_reference_scenario_parses_successfully():
    ref_path = ROOT_DIR / "scenarios" / "reference" / "moving_obstacle_latency.json"
    assert ref_path.exists(), "Reference scenario file must exist"

    with open(ref_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    spec = ScenarioSpec.model_validate(data)
    assert spec.id == "RW-REF-001"
    assert spec.world.width_m == 12.0
    assert spec.world.height_m == 8.0
    assert spec.robot.sensor_latency_ms == 450
    assert len(spec.obstacles) == 1
    assert spec.obstacles[0].speed_mps == 0.45


def test_reject_unknown_fields_in_scenario():
    ref_path = ROOT_DIR / "scenarios" / "reference" / "moving_obstacle_latency.json"
    with open(ref_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["malicious_extra_field"] = "injection"
    with pytest.raises(ValidationError):
        ScenarioSpec.model_validate(data)


def test_reject_nan_and_infinity():
    with pytest.raises(ValidationError):
        Point2D(x_m=float("nan"), y_m=4.0)

    with pytest.raises(ValidationError):
        Point2D(x_m=1.0, y_m=float("inf"))


def test_reject_out_of_bounds_robot_start():
    with pytest.raises(ValidationError):
        ScenarioSpec(
            id="RW-BAD-START",
            kind="static_obstacle",
            seed=1,
            world=WorldSpec(width_m=10.0, height_m=6.0, duration_limit_s=10.0),
            robot=RobotSpec(
                start=Pose2D(x_m=9.95, y_m=4.0, yaw_rad=0.0),  # Radius 0.25 overflows x=10.0
                goal=Point2D(x_m=5.0, y_m=3.0),
                goal_radius_m=0.35,
                body_radius_m=0.25,
                sensor_latency_ms=0,
                sensor_noise_std_m=0.0,
            ),
            obstacles=[],
            oracle=OracleSpec(max_duration_s=10.0),
        )


def test_reject_overlapping_initial_bodies():
    with pytest.raises(ValidationError):
        ScenarioSpec(
            id="RW-OVERLAP",
            kind="static_obstacle",
            seed=1,
            world=WorldSpec(width_m=10.0, height_m=6.0, duration_limit_s=10.0),
            robot=RobotSpec(
                start=Pose2D(x_m=2.0, y_m=2.0, yaw_rad=0.0),
                goal=Point2D(x_m=8.0, y_m=2.0),
                goal_radius_m=0.35,
                body_radius_m=0.30,
                sensor_latency_ms=0,
                sensor_noise_std_m=0.0,
            ),
            obstacles=[
                ObstacleSpec(
                    id="OBS-OVERLAP",
                    shape="circle",
                    radius_m=0.40,
                    motion="static",
                    start=Point2D(x_m=2.1, y_m=2.1),  # Overlaps with robot at (2.0, 2.0)
                    end=Point2D(x_m=2.1, y_m=2.1),
                    speed_mps=0.0,
                )
            ],
            oracle=OracleSpec(max_duration_s=10.0),
        )


def test_policy_config_bounds_and_unknown_fields():
    # Valid policy
    p = PolicyConfig(max_speed_mps=0.8, safe_distance_m=0.5, brake_gain=2.0)
    assert p.max_speed_mps == 0.8

    # Reject speed out of range
    with pytest.raises(ValidationError):
        PolicyConfig(max_speed_mps=5.0)

    # Reject unknown field
    with pytest.raises(ValidationError):
        PolicyConfig.model_validate({"max_speed_mps": 0.5, "unallowed_code": "eval()"})

    # PolicyPatch allows partial whitelist
    patch = PolicyPatch(max_speed_mps=0.4)
    assert patch.max_speed_mps == 0.4
    assert patch.safe_distance_m is None
