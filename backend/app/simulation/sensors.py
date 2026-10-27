"""Deterministic sensor queue with delayed and noisy observations."""
import math
import random
from collections import deque
from typing import Dict, List, Optional
from app.schemas.policy import RelativeObstacleObservation, SensorObservation
from app.schemas.scenario import Pose2D, RobotSpec

class SensorSystem:
    def __init__(self, robot_spec: RobotSpec, dt: float, seed: int):
        self.spec = robot_spec
        self.dt = dt
        self.rng = random.Random(seed + 1000)
        self.latency_ticks = math.ceil((robot_spec.sensor_latency_ms / 1000.0) / dt)
        self.queue: deque = deque()

    def capture_observation(
        self,
        current_tick: int,
        sim_time_s: float,
        true_robot_pose: Pose2D,
        true_obstacles: List[Dict[str, float]],
    ) -> None:
        """Capture ground truth at tick k and enqueue for delivery at k + latency_ticks."""
        delivery_tick = current_tick + self.latency_ticks

        # Compute relative observations for obstacles within range
        rel_obstacles = []
        for obs in true_obstacles:
            dx = obs["x_m"] - true_robot_pose.x_m
            dy = obs["y_m"] - true_robot_pose.y_m
            center_dist = math.hypot(dx, dy)
            surface_dist = center_dist - obs["radius_m"] - self.spec.body_radius_m

            if surface_dist <= self.spec.sensor_range_m:
                # Add deterministic Gaussian noise if configured
                noise_x = self.rng.gauss(0, self.spec.sensor_noise_std_m) if self.spec.sensor_noise_std_m > 0 else 0.0
                noise_y = self.rng.gauss(0, self.spec.sensor_noise_std_m) if self.spec.sensor_noise_std_m > 0 else 0.0

                rel_obstacles.append(
                    RelativeObstacleObservation(
                        id=obs["id"],
                        rel_x_m=dx + noise_x,
                        rel_y_m=dy + noise_y,
                        radius_m=obs["radius_m"],
                        distance_m=max(0.0, surface_dist),
                    )
                )

        # Compute relative direction to goal
        gdx = self.spec.goal.x_m - true_robot_pose.x_m
        gdy = self.spec.goal.y_m - true_robot_pose.y_m
        gdist = math.hypot(gdx, gdy)

        obs = SensorObservation(
            sample_tick=current_tick,
            delivered_tick=delivery_tick,
            age_s=0.0,  # Will be updated upon delivery
            valid=True,
            observed_pose={
                "x_m": true_robot_pose.x_m,
                "y_m": true_robot_pose.y_m,
                "yaw_rad": true_robot_pose.yaw_rad,
            },
            goal_rel_x_m=gdx,
            goal_rel_y_m=gdy,
            goal_distance_m=gdist,
            obstacles=rel_obstacles,
        )
        self.queue.append(obs)

    def get_delivered_observation(self, current_tick: int, sim_time_s: float) -> SensorObservation:
        """Return the newest observation whose delivery_tick <= current_tick."""
        latest_ready: Optional[SensorObservation] = None
        while self.queue and self.queue[0].delivered_tick <= current_tick:
            latest_ready = self.queue.popleft()

        if latest_ready is not None:
            age_s = (current_tick - latest_ready.sample_tick) * self.dt
            latest_ready.age_s = round(age_s, 6)
            return latest_ready

        # No observation ready yet (startup latency period)
        gdx = self.spec.goal.x_m - self.spec.start.x_m
        gdy = self.spec.goal.y_m - self.spec.start.y_m
        return SensorObservation(
            sample_tick=0,
            delivered_tick=0,
            age_s=round(current_tick * self.dt, 6),
            valid=False,
            observed_pose=None,
            goal_rel_x_m=gdx,
            goal_rel_y_m=gdy,
            goal_distance_m=math.hypot(gdx, gdy),
            obstacles=[],
        )
