"""Baseline navigation policy."""
import math
from app.schemas.policy import ControlCommand, PolicyConfig, SensorObservation

def baseline_policy(obs: SensorObservation, config: PolicyConfig) -> ControlCommand:
    """Deterministic navigation law based solely on delayed SensorObservation."""
    # Heading adjustment towards relative goal vector
    desired_heading = math.atan2(obs.goal_rel_y_m, obs.goal_rel_x_m)
    current_yaw = obs.observed_pose["yaw_rad"] if obs.observed_pose else 0.0

    # Angular error normalized to [-pi, pi)
    heading_err = (desired_heading - current_yaw + math.pi) % (2.0 * math.pi) - math.pi
    angular_cmd = max(-1.5, min(1.5, 2.0 * heading_err))

    # Obstacle avoidance braking
    target_speed = config.max_speed_mps
    for o in obs.obstacles:
        dist = o.distance_m
        effective_safe = config.safe_distance_m + config.reaction_margin_m
        if dist < effective_safe:
            # Apply proportional brake gain
            brake_factor = max(0.0, dist / effective_safe)
            target_speed = min(target_speed, config.max_speed_mps * (brake_factor ** config.brake_gain))

    # Slow down if heading alignment is far off
    if abs(heading_err) > 0.5:
        target_speed *= 0.5

    return ControlCommand(linear_mps=max(0.0, target_speed), angular_radps=angular_cmd)
