"""MPC-lite candidate law (opt-in via RW_CANDIDATE_LAW=mpc).

Receding-horizon control over DELIVERED observations only: each tick it
rolls out a small family of constant (v, omega) trajectories ~2.6 s ahead,
predicting obstacle motion from delivered velocity tracks, rejects any
trajectory whose predicted surface clearance goes critical, and picks the
one with the best goal progress minus clearance/effort penalties. The first
command of the winner is applied; next tick it re-plans.

With no lane-relevant obstacle it delegates to the shared core law, so
open-space behavior is unchanged. Baseline runs never use this.
"""

import math

from app.policies.configurable import _core_navigation_law
from app.schemas.policy import ControlCommand, PolicyConfig, SensorObservation

_DT = 0.12
_STEPS = 22  # ~2.64 s horizon
_SPEED_FRACTIONS = (0.0, 0.25, 0.45, 0.65, 0.85, 1.0)
_OMEGAS = (-1.2, -0.8, -0.4, 0.0, 0.4, 0.8, 1.2)
_CRITICAL_CLEARANCE_M = 0.02
_PREFERRED_CLEARANCE_M = 0.28
_ENGAGE_DISTANCE_M = 3.5


class MpcCandidatePolicy:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        pass  # receding horizon is stateless; reset() satisfies the runner hook

    def __call__(self, obs: SensorObservation, config: PolicyConfig) -> ControlCommand:
        if obs.observed_pose is None or not obs.obstacles:
            return _core_navigation_law(obs, config)
        nearest = min(o.distance_m for o in obs.obstacles)
        if nearest > _ENGAGE_DISTANCE_M:
            return _core_navigation_law(obs, config)
        planned = self._plan(obs, config)
        if planned is None:
            # Every rollout is critical: brake and turn toward the goal.
            return _core_navigation_law(obs, config)
        return planned

    # -- rollout machinery ----------------------------------------------
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
        best: tuple[float, float, float] | None = None  # (cost, v, omega)
        best_relaxed: tuple[float, float, float] | None = None

        for fraction in _SPEED_FRACTIONS:
            v = fraction * config.max_speed_mps
            for omega in _OMEGAS:
                x, y, heading = rx, ry, yaw
                min_clearance = float("inf")
                clearance_penalty = 0.0
                rejected = False
                for step in range(1, _STEPS + 1):
                    t = step * _DT
                    heading += omega * _DT
                    x += v * math.cos(heading) * _DT
                    y += v * math.sin(heading) * _DT
                    for obstacle in obstacles:
                        ox = obstacle["x"] + obstacle["vx"] * t
                        oy = obstacle["y"] + obstacle["vy"] * t
                        surface = math.hypot(ox - x, oy - y) - obstacle["r"] - obstacle["body"]
                        if surface < min_clearance:
                            min_clearance = surface
                        if surface < _CRITICAL_CLEARANCE_M:
                            rejected = True
                            break
                        if surface < safe:
                            clearance_penalty += (safe - surface) * _DT
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
                    + 0.05 * abs(omega)
                    + (0.25 if v == 0.0 else 0.0)  # sitting still must earn its keep
                )
                candidate = (cost, v, omega)
                if best_relaxed is None or cost < best_relaxed[0]:
                    best_relaxed = candidate
                # Preferred tier: predicted clearance never drops under the
                # safety floor (oracle limit + margin). Only if no such
                # trajectory exists do we relax to merely non-critical ones.
                if min_clearance >= _PREFERRED_CLEARANCE_M:
                    if best is None or cost < best[0]:
                        best = candidate

        if best is None:
            best = best_relaxed
        if best is None:
            return None
        _, v_best, omega_best = best
        return ControlCommand(
            linear_mps=max(0.0, min(1.5, v_best)),
            angular_radps=max(-math.pi, min(math.pi, omega_best)),
        )
