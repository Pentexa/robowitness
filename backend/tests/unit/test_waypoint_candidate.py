"""Waypoint planner tests: waypoint choice, reach-and-resume, opt-in wiring."""

import math

import pytest
from app.config import settings
from app.policies.candidate_law import get_candidate_policy_fn
from app.policies.waypoint_candidate import WaypointCandidatePolicy
from app.schemas.policy import (
    ObstacleTrack,
    PolicyConfig,
    RelativeObstacleObservation,
    SensorObservation,
)

CONFIG = PolicyConfig(
    id="candidate-final-v1",
    max_speed_mps=0.60,
    safe_distance_m=1.00,
    reaction_margin_m=0.20,
    brake_gain=4.0,
    obstacle_prediction_horizon_s=1.00,
)


def _obs(obstacles=None, tracks=None) -> SensorObservation:
    return SensorObservation(
        sample_tick=0,
        delivered_tick=0,
        age_s=0.0,
        valid=True,
        observed_pose={"x_m": 1.0, "y_m": 4.0, "yaw_rad": 0.0},
        goal_rel_x_m=10.0,
        goal_rel_y_m=0.0,
        goal_distance_m=10.0,
        obstacles=obstacles or [],
        tracks=tracks or [],
    )


def test_waypoint_chosen_on_vacating_side():
    policy = WaypointCandidatePolicy()
    obstacle = RelativeObstacleObservation(
        id="O1", rel_x_m=3.0, rel_y_m=0.8, radius_m=0.33, distance_m=2.6
    )
    # Obstacle moving south (vy<0): vacated side is north (+y in lane frame).
    track = ObstacleTrack(id="O1", vx_mps=0.0, vy_mps=-0.4, samples=10, confident=True)
    policy._choose_waypoint(_obs([obstacle], [track]))
    assert policy._waypoint is not None
    wx, wy = policy._waypoint
    assert wx == pytest.approx(1.0 + 3.0)
    assert wy > 4.0 + 0.8  # north of the obstacle center


def test_waypoint_clears_and_reset_isolates():
    policy = WaypointCandidatePolicy()
    policy._waypoint = (1.2, 4.1)  # within reach of pose (1,4)
    policy._waypoint_obstacle_id = "O1"
    cmd = policy(_obs(), CONFIG)
    assert cmd.linear_mps > 0
    assert policy._waypoint is None  # reached -> resumed to real goal
    policy._waypoint = (5.0, 5.0)
    policy.reset()
    assert policy._waypoint is None


def test_waypoint_opt_in_wiring():
    previous = settings.RW_CANDIDATE_LAW
    settings.RW_CANDIDATE_LAW = "waypoint"
    try:
        assert isinstance(get_candidate_policy_fn(), WaypointCandidatePolicy)
    finally:
        settings.RW_CANDIDATE_LAW = previous


def test_no_obstacle_goes_straight():
    policy = WaypointCandidatePolicy()
    cmd = policy(_obs(), CONFIG)
    assert cmd.linear_mps == pytest.approx(CONFIG.max_speed_mps)
    assert math.isclose(cmd.angular_radps, 0.0, abs_tol=1e-9)
