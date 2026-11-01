"""Configurable navigation policy."""

import math
from app.schemas.policy import ControlCommand, PolicyConfig, SensorObservation

# Fixed avoidance blend gain (NOT a tunable parameter: only the five numeric
# PolicyConfig fields may differ between baseline and candidate runs).
_AVOID_GAIN = 2.0


def configurable_policy(obs: SensorObservation, config: PolicyConfig) -> ControlCommand:
    """Configurable navigation policy parameterized by the 5 allowed numeric fields.

    Single shared navigation law used for BOTH baseline and candidate runs;
    only the five numeric PolicyConfig values may differ between runs.
    Sees only delayed SensorObservation (plus deterministic velocity tracks
    derived solely from delivered observations), never ground truth.
    """
    return _core_navigation_law(obs, config)


def _core_navigation_law(obs: SensorObservation, config: PolicyConfig) -> ControlCommand:
    """Shared deterministic navigation law: proportional heading + delayed-sensor
    braking + horizon-gated lateral avoidance from delivered velocity tracks.

    With obstacle_prediction_horizon_s == 0 the avoidance block is skipped
    entirely, so the baseline behaves bit-identically to the brake-only law.
    """
    current_yaw = obs.observed_pose["yaw_rad"] if obs.observed_pose else 0.0

    goal_x, goal_y = obs.goal_rel_x_m, obs.goal_rel_y_m
    avoid_mag = 0.0
    if config.obstacle_prediction_horizon_s > 0 and obs.observed_pose:
        # Blend in direction space: normalize the goal vector FIRST so a
        # distant goal cannot drown the avoidance term, then add avoidance.
        goal_norm = math.hypot(goal_x, goal_y) or 1.0
        goal_x, goal_y, avoid_mag = _apply_avoidance(
            obs, config, current_yaw, goal_x / goal_norm, goal_y / goal_norm
        )
        desired_heading = math.atan2(goal_y, goal_x)
    else:
        # Untouched baseline path (horizon == 0): bit-identical behavior.
        desired_heading = math.atan2(obs.goal_rel_y_m, obs.goal_rel_x_m)

    heading_err = (desired_heading - current_yaw + math.pi) % (2.0 * math.pi) - math.pi
    angular_cmd = max(-1.5, min(1.5, 2.0 * heading_err))

    target_speed = config.max_speed_mps
    # Prediction horizon widens the effective safety margin once, not per obstacle.
    effective_safe = config.safe_distance_m + config.reaction_margin_m
    if config.obstacle_prediction_horizon_s > 0:
        effective_safe += config.max_speed_mps * config.obstacle_prediction_horizon_s * 0.5

    for o in obs.obstacles:
        dist = o.distance_m
        if dist < effective_safe:
            brake_factor = max(0.0, dist / effective_safe)
            target_speed = min(
                target_speed, config.max_speed_mps * (brake_factor**config.brake_gain)
            )

    # Heading-alignment slowdown applies to goal tracking only: when avoidance
    # is actively steering (intentional misalignment), do not fight it.
    # Horizon-gated via avoid_mag (baseline horizon=0 keeps old behavior).
    if abs(heading_err) > 0.5 and avoid_mag <= 0.15:
        target_speed *= 0.5

    # Anti-sitting-duck: when avoidance is strongly active the escape heading is
    # meaningful, so keep creeping along it instead of braking to a full stop
    # inside the sweep band. Horizon-gated (baseline horizon=0 unaffected).
    # Fixed fraction, documented here — not a sixth tunable parameter.
    if avoid_mag > 0.15:
        target_speed = max(target_speed, 0.40 * config.max_speed_mps * min(1.0, avoid_mag))

    return ControlCommand(linear_mps=max(0.0, target_speed), angular_radps=angular_cmd)


def _apply_avoidance(
    obs: SensorObservation,
    config: PolicyConfig,
    yaw: float,
    goal_x: float,
    goal_y: float,
):
    """Blend a lateral escape vector into the goal vector.

    For each confidently-tracked obstacle, predict its robot-frame relative
    position horizon seconds ahead (using only delivered track velocities) and,
    inside the influence radius, push the desired heading away from the
    predicted sweep band. Missing history is handled conservatively upstream
    (confident=False tracks are ignored here).
    """
    horizon = config.obstacle_prediction_horizon_s
    cos_y, sin_y = math.cos(-yaw), math.sin(-yaw)
    avoid_x, avoid_y = 0.0, 0.0
    tracks = {t.id: t for t in obs.tracks}
    for o in obs.obstacles:
        track = tracks.get(o.id)
        if track is None or not track.confident:
            continue
        # World-frame velocity -> robot frame (observed yaw only).
        vrx = track.vx_mps * cos_y - track.vy_mps * sin_y
        vry = track.vx_mps * sin_y + track.vy_mps * cos_y
        px = o.rel_x_m + vrx * horizon
        py = o.rel_y_m + vry * horizon
        dist_center = math.hypot(px, py)
        if dist_center < 1e-6:
            continue
        surface_d = dist_center - o.radius_m
        # Influence grows with own speed (stopping distance) AND with the
        # obstacle's delivered speed (fast crossers need earlier reaction).
        # Horizon-gated: baseline (horizon=0) keeps the static margin.
        influence = (
            config.safe_distance_m
            + config.reaction_margin_m
            + 0.5 * config.max_speed_mps * horizon
            + o.radius_m
            + 0.5 * math.hypot(vrx, vry) * horizon
        )
        if surface_d < influence:
            w = max(0.0, 1.0 - surface_d / influence)
            avoid_x += (-px / dist_center) * w
            avoid_y += (-py / dist_center) * w
    avoid_mag = math.hypot(avoid_x, avoid_y)
    return goal_x + _AVOID_GAIN * avoid_x, goal_y + _AVOID_GAIN * avoid_y, avoid_mag
