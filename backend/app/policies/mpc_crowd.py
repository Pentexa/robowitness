"""Crowd-tuned MPC variant (opt-in via RW_CANDIDATE_LAW=mpc-crowd).

Dense pedestrian traffic breaks the verified MPC configuration in two
specific ways, and this variant addresses exactly those without touching
the verified one's parameters:

1. Prediction uncertainty grows over the horizon — with 300-500 ms sensor
   latency plus noise, where a pedestrian *will be* in 2 s is a cone, not a
   point. Predicted obstacle radii inflate over time (0.10 m + 0.12 m/s).
2. Open-loop constant-turn rollouts dance in a crowd. This variant rolls
   out CLOSED-LOOP trajectories: at every simulated step the heading is
   re-aimed at the goal with a radial avoidance push from predicted
   obstacle positions, and only the speed profile is searched. The robot
   therefore commits to threading gaps instead of orbiting them.

The verified configuration (`mpc`) is unchanged; this is a separate,
separately-measured law for crowd scenarios.
"""

import math

from app.policies.configurable import _core_navigation_law
from app.policies.mpc_candidate import MpcCandidatePolicy
from app.schemas.policy import ControlCommand, PolicyConfig, SensorObservation


class MpcCrowdPolicy(MpcCandidatePolicy):
    STEPS = 30  # ~3.6 s at DT=0.12
    SPEED_FRACTIONS = (0.0, 0.25, 0.45, 0.65, 0.85, 1.0)
    UNCERTAINTY_BASE_M = 0.10
    UNCERTAINTY_RATE_MPS = 0.12
    ENGAGE_DISTANCE_M = 4.0

    # -- closed-loop rollout ---------------------------------------------
    def _plan(self, obs: SensorObservation, config: PolicyConfig) -> ControlCommand | None:
        pose = obs.observed_pose
        assert pose is not None
        rx, ry, yaw = pose["x_m"], pose["y_m"], pose["yaw_rad"]
        goal_x, goal_y = rx + obs.goal_rel_x_m, ry + obs.goal_rel_y_m

        tracks = {t.id: t for t in obs.tracks}
        obstacles = []
        for obstacle in obs.obstacles:
            center_dist = math.hypot(obstacle.rel_x_m, obstacle.rel_y_m)
            body_radius = max(0.05, center_dist - obstacle.distance_m - obstacle.radius_m)
            track = tracks.get(obstacle.id)
            vx = track.vx_mps if track is not None and track.confident else 0.0
            vy = track.vy_mps if track is not None and track.confident else 0.0
            obstacles.append(
                {
                    "x": rx + obstacle.rel_x_m,
                    "y": ry + obstacle.rel_y_m,
                    "r": obstacle.radius_m,
                    "body": body_radius,
                    "vx": vx,
                    "vy": vy,
                }
            )

        safe = config.safe_distance_m + config.reaction_margin_m
        start_goal_dist = math.hypot(goal_x - rx, goal_y - ry)
        best: tuple[float, float, float] | None = None
        best_relaxed: tuple[float, float, float] | None = None

        for fraction in self.SPEED_FRACTIONS:
            v = fraction * config.max_speed_mps
            x, y, heading = rx, ry, yaw
            first_omega = 0.0
            min_clearance = float("inf")
            clearance_penalty = 0.0
            rejected = False
            for step in range(1, self.STEPS + 1):
                t = step * self.DT
                # Closed-loop heading: goal pull + radial push from where
                # each pedestrian is predicted to be at this step.
                desired_x, desired_y = goal_x - x, goal_y - y
                for obstacle in obstacles:
                    ox = obstacle["x"] + obstacle["vx"] * t
                    oy = obstacle["y"] + obstacle["vy"] * t
                    dx, dy = x - ox, y - oy
                    dist = math.hypot(dx, dy)
                    influence = safe + obstacle["r"] + obstacle["body"]
                    if 1e-6 < dist < influence:
                        w = 1.0 - dist / influence
                        desired_x += (dx / dist) * w * 2.0
                        desired_y += (dy / dist) * w * 2.0
                desired_heading = math.atan2(desired_y, desired_x)
                heading_err = (desired_heading - heading + math.pi) % (2 * math.pi) - math.pi
                omega = max(-1.5, min(1.5, 2.0 * heading_err))
                if step == 1:
                    first_omega = omega
                heading += omega * self.DT
                x += v * math.cos(heading) * self.DT
                y += v * math.sin(heading) * self.DT
                uncertainty = self.UNCERTAINTY_BASE_M + self.UNCERTAINTY_RATE_MPS * t
                for obstacle in obstacles:
                    ox = obstacle["x"] + obstacle["vx"] * t
                    oy = obstacle["y"] + obstacle["vy"] * t
                    surface = (
                        math.hypot(ox - x, oy - y) - obstacle["r"] - obstacle["body"] - uncertainty
                    )
                    min_clearance = min(min_clearance, surface)
                    if surface < 0.02:
                        rejected = True
                        break
                    if surface < safe:
                        clearance_penalty += (safe - surface) * self.DT
                if rejected:
                    break
            if rejected:
                continue
            final_goal_dist = math.hypot(goal_x - x, goal_y - y)
            progress = start_goal_dist - final_goal_dist
            cost = (
                final_goal_dist
                - 0.35 * progress
                + 1.6 * clearance_penalty
                + (0.25 if v == 0.0 else 0.0)
            )
            candidate = (cost, v, first_omega)
            if best_relaxed is None or cost < best_relaxed[0]:
                best_relaxed = candidate
            if min_clearance >= 0.28:
                if best is None or cost < best[0]:
                    best = candidate

        chosen = best if best is not None else best_relaxed
        if chosen is None:
            return None
        _, v_best, omega_best = chosen
        return ControlCommand(
            linear_mps=max(0.0, min(1.5, v_best)),
            angular_radps=max(-math.pi, min(math.pi, omega_best)),
        )

    def __call__(self, obs: SensorObservation, config: PolicyConfig) -> ControlCommand:
        if obs.observed_pose is None or not obs.obstacles:
            return _core_navigation_law(obs, config)
        nearest = min(o.distance_m for o in obs.obstacles)
        if nearest > self.ENGAGE_DISTANCE_M:
            return _core_navigation_law(obs, config)
        planned = self._plan(obs, config)
        return planned if planned is not None else _core_navigation_law(obs, config)
