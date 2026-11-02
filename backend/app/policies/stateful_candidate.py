"""Stateful candidate planner (opt-in via RW_CANDIDATE_LAW=stateful).

Why stateful: the shared stateless law re-decides its escape side every tick
and can oscillate along an obstacle sweep until the oracle's stuck rule
fires. This planner adds two pieces of per-run memory on top of the SAME
core law (it never sees ground truth either):

1. Side commitment — when an obstacle blocks the goal lane, it commits to
   passing on the side the obstacle is vacating (behind its lateral motion)
   and keeps that side until the obstacle is behind the robot.
2. Stall breaker — if goal progress stalls for > ~2 s while no obstacle is
   critically close, it widens the committed detour and enforces a creep
   floor instead of sitting in the sweep band.

The baseline law is untouched: this class is used only where a candidate
policy function is requested and the setting enables it. The runner calls
reset() before every run, so no state leaks between scenarios.
"""

import math

from app.policies.configurable import _core_navigation_law
from app.schemas.policy import ControlCommand, PolicyConfig, SensorObservation

_SHIFT_M = 1.5
_SHIFT_STALLED_M = 2.3
_STALL_TICKS = 120  # ~2 s at 60 Hz (stall-breaker floor threshold)
_STALL_REACT_TICKS = 60  # ~1 s: detour shift starts here, before oracle's 3 s
_CRITICAL_CLEARANCE_M = 0.30


class StatefulCandidatePolicy:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._committed_side: dict[str, float] = {}
        self._last_goal_dist: float | None = None
        self._stall_ticks: int = 0

    # -- memory helpers -------------------------------------------------
    def _track_progress(self, obs: SensorObservation) -> None:
        goal_dist = obs.goal_distance_m
        if self._last_goal_dist is None or (self._last_goal_dist - goal_dist) >= 0.05:
            self._last_goal_dist = goal_dist
            self._stall_ticks = 0
        else:
            self._stall_ticks += 1

    def _blocking_obstacle(self, obs: SensorObservation):
        """Nearest obstacle ahead that actually blocks the goal lane."""
        goal_dist = math.hypot(obs.goal_rel_x_m, obs.goal_rel_y_m)
        if goal_dist < 1e-6:
            return None, (1.0, 0.0)
        ux, uy = obs.goal_rel_x_m / goal_dist, obs.goal_rel_y_m / goal_dist
        best = None
        for obstacle in obs.obstacles:
            along = obstacle.rel_x_m * ux + obstacle.rel_y_m * uy
            lateral = ux * obstacle.rel_y_m - uy * obstacle.rel_x_m
            if along <= 0.0:
                # Passed it: drop any commitment for this obstacle.
                self._committed_side.pop(obstacle.id, None)
                continue
            if abs(lateral) < obstacle.radius_m + 0.9 and obstacle.distance_m < 2.5:
                if best is None or obstacle.distance_m < best.distance_m:
                    best = obstacle
        return best, (ux, uy)

    def _shifted_observation(self, obs: SensorObservation) -> SensorObservation:
        blocking, (ux, uy) = self._blocking_obstacle(obs)
        if blocking is None:
            return obs
        # Reactive only: a proactive detour damaged healthy runs. Intervene
        # once a stall is actually forming (but before the oracle's ~3 s
        # stuck window closes); healthy avoidance episodes stay untouched.
        if self._stall_ticks <= _STALL_REACT_TICKS:
            return obs
        if blocking.id not in self._committed_side:
            tracks = {t.id: t for t in obs.tracks}
            track = tracks.get(blocking.id)
            side: float
            if track is not None and track.confident:
                lateral_velocity = ux * track.vy_mps - uy * track.vx_mps
                if abs(lateral_velocity) > 0.05:
                    # Pass behind: the side the obstacle is moving AWAY from.
                    side = -math.copysign(1.0, lateral_velocity)
                else:
                    lateral = ux * blocking.rel_y_m - uy * blocking.rel_x_m
                    side = -math.copysign(1.0, lateral) if lateral != 0 else 1.0
            else:
                lateral = ux * blocking.rel_y_m - uy * blocking.rel_x_m
                side = -math.copysign(1.0, lateral) if lateral != 0 else 1.0
            self._committed_side[blocking.id] = side
        side = self._committed_side[blocking.id]
        shift = _SHIFT_STALLED_M if self._stall_ticks > _STALL_TICKS else _SHIFT_M
        perp_x, perp_y = -uy, ux
        new_goal_x = obs.goal_rel_x_m + perp_x * side * shift
        new_goal_y = obs.goal_rel_y_m + perp_y * side * shift
        return obs.model_copy(
            update={
                "goal_rel_x_m": new_goal_x,
                "goal_rel_y_m": new_goal_y,
                "goal_distance_m": math.hypot(new_goal_x, new_goal_y),
            }
        )

    # -- policy entry point ---------------------------------------------
    def __call__(self, obs: SensorObservation, config: PolicyConfig) -> ControlCommand:
        self._track_progress(obs)
        command = _core_navigation_law(self._shifted_observation(obs), config)
        if self._stall_ticks > _STALL_TICKS:
            nearest = min((o.distance_m for o in obs.obstacles), default=None)
            if nearest is None or nearest > _CRITICAL_CLEARANCE_M:
                floor = 0.35 * config.max_speed_mps
                if command.linear_mps < floor:
                    command = ControlCommand(linear_mps=floor, angular_radps=command.angular_radps)
        return command
