"""Configurable navigation policy."""
import math
from app.schemas.policy import ControlCommand, PolicyConfig, SensorObservation

def configurable_policy(obs: SensorObservation, config: PolicyConfig) -> ControlCommand:
    """Configurable navigation policy parameterized by the 5 allowed numeric fields."""
    desired_heading = math.atan2(obs.goal_rel_y_m, obs.goal_rel_x_m)
    current_yaw = obs.observed_pose["yaw_rad"] if obs.observed_pose else 0.0

    heading_err = (desired_heading - current_yaw + math.pi) % (2.0 * math.pi) - math.pi
    angular_cmd = max(-1.5, min(1.5, 2.0 * heading_err))

    target_speed = config.max_speed_mps
    effective_safe = config.safe_distance_m + config.reaction_margin_m

    for o in obs.obstacles:
        dist = o.distance_m
        # Account for prediction horizon if configured
        if config.obstacle_prediction_horizon_s > 0:
            effective_safe += (config.max_speed_mps * config.obstacle_prediction_horizon_s * 0.5)

        if dist < effective_safe:
            brake_factor = max(0.0, dist / effective_safe)
            target_speed = min(target_speed, config.max_speed_mps * (brake_factor ** config.brake_gain))

    if abs(heading_err) > 0.5:
        target_speed *= 0.5

    return ControlCommand(linear_mps=max(0.0, target_speed), angular_radps=angular_cmd)
