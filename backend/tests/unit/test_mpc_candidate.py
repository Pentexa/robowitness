"""MPC-lite candidate tests: planning sanity, rejection fallback, wiring."""

import pytest
from app.config import settings
from app.policies.candidate_law import get_candidate_policy_fn
from app.policies.mpc_candidate import MpcCandidatePolicy
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


def _obs(obstacles=None, tracks=None, goal=(10.0, 0.0)) -> SensorObservation:
    return SensorObservation(
        sample_tick=0,
        delivered_tick=0,
        age_s=0.0,
        valid=True,
        observed_pose={"x_m": 1.0, "y_m": 4.0, "yaw_rad": 0.0},
        goal_rel_x_m=goal[0],
        goal_rel_y_m=goal[1],
        goal_distance_m=(goal[0] ** 2 + goal[1] ** 2) ** 0.5,
        obstacles=obstacles or [],
        tracks=tracks or [],
    )


def test_free_lane_goes_fast():
    policy = MpcCandidatePolicy()
    cmd = policy(_obs(), CONFIG)
    assert cmd.linear_mps == pytest.approx(CONFIG.max_speed_mps)


def test_head_on_obstacle_produces_turn_or_slowdown():
    policy = MpcCandidatePolicy()
    obstacle = RelativeObstacleObservation(
        id="O1", rel_x_m=2.2, rel_y_m=0.0, radius_m=0.35, distance_m=1.6
    )
    track = ObstacleTrack(id="O1", vx_mps=0.0, vy_mps=0.0, samples=10, confident=True)
    cmd = policy(_obs([obstacle], [track]), CONFIG)
    # Any safe plan must deviate from full-speed straight ahead.
    assert cmd.angular_radps != 0.0 or cmd.linear_mps < CONFIG.max_speed_mps


def test_mpc_opt_in_wiring():
    previous = settings.RW_CANDIDATE_LAW
    settings.RW_CANDIDATE_LAW = "mpc"
    try:
        assert isinstance(get_candidate_policy_fn(), MpcCandidatePolicy)
    finally:
        settings.RW_CANDIDATE_LAW = previous
