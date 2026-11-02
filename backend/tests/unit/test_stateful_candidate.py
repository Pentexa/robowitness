"""Stateful candidate planner tests: reset isolation, side commitment, opt-in."""

import pytest
from app.config import settings
from app.policies.candidate_law import get_candidate_policy_fn
from app.policies.configurable import configurable_policy
from app.policies.stateful_candidate import StatefulCandidatePolicy
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


def _obs(goal=(8.0, 0.0), obstacles=None, tracks=None) -> SensorObservation:
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


def test_default_law_is_shared_stateless():
    assert settings.RW_CANDIDATE_LAW == "shared"
    assert get_candidate_policy_fn() is configurable_policy


def test_stateful_opt_in_returns_fresh_instances():
    previous = settings.RW_CANDIDATE_LAW
    settings.RW_CANDIDATE_LAW = "stateful"
    try:
        first, second = get_candidate_policy_fn(), get_candidate_policy_fn()
        assert isinstance(first, StatefulCandidatePolicy)
        assert first is not second
    finally:
        settings.RW_CANDIDATE_LAW = previous


def test_side_commitment_shifts_goal_behind_moving_obstacle():
    policy = StatefulCandidatePolicy()
    policy._stall_ticks = 100  # reactive gate: detour only once a stall forms
    obstacle = RelativeObstacleObservation(
        id="O1", rel_x_m=2.0, rel_y_m=1.0, radius_m=0.33, distance_m=1.8
    )
    # Obstacle north of the lane moving south (vy<0): vacated side is north (+).
    track = ObstacleTrack(id="O1", vx_mps=0.0, vy_mps=-0.4, samples=10, confident=True)
    shifted = policy._shifted_observation(_obs(obstacles=[obstacle], tracks=[track]))
    assert policy._committed_side["O1"] == pytest.approx(1.0)
    assert shifted.goal_rel_y_m > 0.0  # virtual goal shifted north

    # Commitment persists even if the obstacle drifts; reset clears it.
    policy.reset()
    assert policy._committed_side == {}
    assert policy._stall_ticks == 0


def test_stall_breaker_floor_after_long_stall():
    policy = StatefulCandidatePolicy()
    policy._stall_ticks = 200
    policy._last_goal_dist = 5.0
    cmd = policy(_obs(), CONFIG)
    assert cmd.linear_mps >= 0.35 * CONFIG.max_speed_mps


def test_no_obstacle_matches_core_law_direction():
    policy = StatefulCandidatePolicy()
    cmd = policy(_obs(), CONFIG)
    assert cmd.linear_mps > 0
