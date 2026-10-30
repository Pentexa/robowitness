"""Policy contract tests: bounded outputs, patch sensitivity, ground-truth isolation."""
import inspect
import math
import app.policies.baseline as baseline_mod
import app.policies.configurable as configurable_mod
from app.policies.baseline import baseline_policy
from app.policies.configurable import configurable_policy
from app.schemas.policy import PolicyConfig, SensorObservation


def _obs(**kw):
    base = dict(sample_tick=27, delivered_tick=27, age_s=0.45, valid=True,
                observed_pose={"x_m": 2.0, "y_m": 4.0, "yaw_rad": 0.0},
                goal_rel_x_m=9.0, goal_rel_y_m=0.0, goal_distance_m=9.0,
                obstacles=[])
    base.update(kw)
    return SensorObservation(**base)


def test_commands_finite_and_bounded():
    cfg = PolicyConfig()
    for obs in [_obs(),
                _obs(obstacles=[{"id": "O1", "rel_x_m": 0.1, "rel_y_m": 0.0,
                                 "radius_m": 0.35, "distance_m": 0.01}]),
                _obs(valid=False, observed_pose=None)]:
        for fn in (baseline_policy, configurable_policy):
            cmd = fn(obs, cfg)
            assert math.isfinite(cmd.linear_mps) and math.isfinite(cmd.angular_radps)
            assert -0.5 <= cmd.linear_mps <= 1.5
            assert -math.pi <= cmd.angular_radps <= math.pi
            assert cmd.linear_mps >= 0.0


def test_parameter_patch_changes_behavior():
    near = _obs(obstacles=[{"id": "O1", "rel_x_m": 0.5, "rel_y_m": 0.0,
                             "radius_m": 0.35, "distance_m": 0.2}])
    loose = PolicyConfig(safe_distance_m=0.2, reaction_margin_m=0.0)
    tight = PolicyConfig(safe_distance_m=1.5, reaction_margin_m=0.5)
    assert configurable_policy(near, tight).linear_mps < configurable_policy(near, loose).linear_mps


def test_baseline_and_configurable_share_single_law():
    cfg = PolicyConfig(obstacle_prediction_horizon_s=0.6)
    cases = [_obs(), _obs(obstacles=[{"id": "O1", "rel_x_m": 1.0, "rel_y_m": 0.2,
                                       "radius_m": 0.35, "distance_m": 0.6}])]
    for o in cases:
        b, c = baseline_policy(o, cfg), configurable_policy(o, cfg)
        assert (b.linear_mps, b.angular_radps) == (c.linear_mps, c.angular_radps)


def test_policies_never_touch_ground_truth_or_oracle():
    for mod in (baseline_mod, configurable_mod):
        src = inspect.getsource(mod)
        for forbidden in ("ScenarioSpec", "oracle", "ground_truth", "getContactPoints",
                          "performCollisionDetection", "app.simulation", "app.verification"):
            assert forbidden not in src, f"{mod.__name__} references {forbidden}"
