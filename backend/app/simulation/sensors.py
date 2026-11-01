"""Deterministic sensor queue with delayed and noisy observations."""

import math
import random
from collections import deque
from typing import Dict, List, Optional
from app.schemas.policy import (
    ObstacleTrack,
    RelativeObstacleObservation,
    SensorObservation,
)
from app.schemas.scenario import Pose2D, RobotSpec

# Fixed regression window for velocity estimation (deterministic, documented).
# 16 delivered samples (~0.27 s at 60 Hz) halves noise-induced velocity error
# versus 8 samples; lag cost (~7 cm at 0.5 m/s) is acceptable for avoidance.
_TRACK_WINDOW = 16

# Beam (LiDAR-like) model: fixed ray fan used only when RW_SENSOR_MODEL=beam.
_BEAM_COUNT = 24


def _beam_estimate(dx: float, dy: float, radius_m: float, body_radius_m: float):
    """Quantize an obstacle sighting to the nearest LiDAR ray.

    Returns (rel_x_m, rel_y_m, surface_distance_m) estimated from the ray hit,
    or None if no ray strikes the obstacle disc. The reported position sits on
    the hitting ray at the disc's near intersection — bearing is quantized to
    the ray fan exactly like a real scanner's angular resolution.
    """
    center_dist = math.hypot(dx, dy)
    if center_dist <= 0.0:
        return None
    center_angle = math.atan2(dy, dx)
    half_width = math.asin(min(1.0, radius_m / center_dist))
    step = 2.0 * math.pi / _BEAM_COUNT
    # Nearest ray index to the obstacle's center bearing.
    k = round(center_angle / step)
    ray_angle = k * step
    angle_diff = abs((ray_angle - center_angle + math.pi) % (2.0 * math.pi) - math.pi)
    if angle_diff > half_width:
        return None
    # Ray-disc intersection (near side), along the ray direction.
    proj = center_dist * math.cos(angle_diff)
    perp_sq = center_dist**2 - proj**2
    disc = radius_m**2 - perp_sq
    if disc < 0.0:
        return None
    hit_center_dist = proj  # center projected on ray; near point is hit_center - sqrt(disc)
    near_dist = hit_center_dist - math.sqrt(disc)
    surface_dist = max(0.0, near_dist - body_radius_m)
    ux, uy = math.cos(ray_angle), math.sin(ray_angle)
    return ux * hit_center_dist, uy * hit_center_dist, surface_dist


class SensorSystem:
    def __init__(self, robot_spec: RobotSpec, dt: float, seed: int, beam_mode: bool = False):
        self.spec = robot_spec
        self.dt = dt
        self.beam_mode = beam_mode
        self.rng = random.Random(seed + 1000)
        self.latency_ticks = math.ceil((robot_spec.sensor_latency_ms / 1000.0) / dt)
        self.queue: deque = deque()
        # Per-obstacle history of DELIVERED world-frame estimates:
        # id -> deque[(sample_tick, x_m, y_m)], bounded, deterministic.
        self.history: Dict[str, deque] = {}

    def capture_observation(
        self,
        current_tick: int,
        sim_time_s: float,
        true_robot_pose: Pose2D,
        true_obstacles: List[Dict[str, float]],
    ) -> None:
        """Capture ground truth at tick k and enqueue for delivery at k + latency_ticks."""
        delivery_tick = current_tick + self.latency_ticks

        # Compute relative observations for obstacles within range.
        # Occlusion: an obstacle hidden behind a closer one (the line of sight
        # passes through the closer obstacle's body) is not observed at all —
        # a real range sensor cannot see through it.
        rel_obstacles = []
        for idx, obs in enumerate(true_obstacles):
            dx = obs["x_m"] - true_robot_pose.x_m
            dy = obs["y_m"] - true_robot_pose.y_m
            center_dist = math.hypot(dx, dy)
            surface_dist = center_dist - obs["radius_m"] - self.spec.body_radius_m

            if surface_dist <= self.spec.sensor_range_m and not _is_occluded(
                idx, true_obstacles, true_robot_pose
            ):
                if self.beam_mode:
                    estimate = _beam_estimate(dx, dy, obs["radius_m"], self.spec.body_radius_m)
                    if estimate is None:
                        continue  # no LiDAR ray struck this obstacle on this scan
                    dx, dy, surface_dist = estimate
                # Add deterministic Gaussian noise if configured
                noise_x = (
                    self.rng.gauss(0, self.spec.sensor_noise_std_m)
                    if self.spec.sensor_noise_std_m > 0
                    else 0.0
                )
                noise_y = (
                    self.rng.gauss(0, self.spec.sensor_noise_std_m)
                    if self.spec.sensor_noise_std_m > 0
                    else 0.0
                )

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
            self._record_history(latest_ready)
            latest_ready.tracks = self._compute_tracks()
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
            tracks=[],
        )

    def _record_history(self, obs: SensorObservation) -> None:
        """Store delivered world-frame position estimates per obstacle ID.

        World-frame estimate = delivered robot pose + delivered relative vector.
        Uses ONLY delivered (possibly noisy/stale) data — never ground truth.
        """
        if not obs.observed_pose:
            return
        rx, ry = obs.observed_pose["x_m"], obs.observed_pose["y_m"]
        for o in obs.obstacles:
            hist = self.history.setdefault(o.id, deque(maxlen=_TRACK_WINDOW))
            hist.append((obs.sample_tick, rx + o.rel_x_m, ry + o.rel_y_m))

    def _compute_tracks(self) -> List[ObstacleTrack]:
        """Least-squares velocity over the bounded sample window.

        Confident only with >= 3 samples spanning >= 2 ticks; otherwise the
        policy must treat the obstacle as static (conservative fallback).
        """
        tracks: List[ObstacleTrack] = []
        for oid, hist in self.history.items():
            n = len(hist)
            if n >= 3 and (hist[-1][0] - hist[0][0]) >= 2:
                t0 = hist[0][0]
                xs = [h[1] for h in hist]
                ys = [h[2] for h in hist]
                ts = [(h[0] - t0) * self.dt for h in hist]
                vx = _slope(ts, xs)
                vy = _slope(ts, ys)
                tracks.append(
                    ObstacleTrack(id=oid, vx_mps=vx, vy_mps=vy, samples=n, confident=True)
                )
            else:
                tracks.append(
                    ObstacleTrack(id=oid, vx_mps=0.0, vy_mps=0.0, samples=n, confident=False)
                )
        return tracks


def _is_occluded(idx: int, obstacles: List[Dict[str, float]], pose: Pose2D) -> bool:
    """True if another, closer obstacle's body blocks the line of sight."""
    target = obstacles[idx]
    tx, ty = target["x_m"] - pose.x_m, target["y_m"] - pose.y_m
    target_dist = math.hypot(tx, ty)
    if target_dist <= 0.0:
        return False
    ux, uy = tx / target_dist, ty / target_dist
    for jdx, other in enumerate(obstacles):
        if jdx == idx:
            continue
        ox, oy = other["x_m"] - pose.x_m, other["y_m"] - pose.y_m
        along = ox * ux + oy * uy  # projection onto the line of sight
        if along <= 0.0 or along >= target_dist:
            continue  # behind the sensor or beyond the target: cannot block it
        perp = abs(ox * uy - oy * ux)  # perpendicular distance to the ray
        if perp < other["radius_m"]:
            return True
    return False


def _slope(ts: List[float], vs: List[float]) -> float:
    n = len(ts)
    mean_t = sum(ts) / n
    mean_v = sum(vs) / n
    denom = sum((t - mean_t) ** 2 for t in ts)
    if denom <= 0.0:
        return 0.0
    return sum((t - mean_t) * (v - mean_v) for t, v in zip(ts, vs)) / denom
