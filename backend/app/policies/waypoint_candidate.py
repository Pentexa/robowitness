"""Waypoint candidate planner (opt-in via RW_CANDIDATE_LAW=waypoint).

When an obstacle blocks the goal lane, the planner picks ONE world-frame
waypoint beside the obstacle — on the side the obstacle is vacating — and
steers to that fixed point until it is reached or the obstacle is passed,
then resumes to the real goal. The waypoint is computed only from delivered
observations (observed pose + relative obstacle + track velocity), never
ground truth. Speed/braking still come from the shared core law with the
waypoint substituted as the goal; the real obstacle list is untouched, so
braking and avoidance keep working while approaching the waypoint.
"""

import math

from app.policies.configurable import _core_navigation_law
from app.schemas.policy import ControlCommand, PolicyConfig, SensorObservation

_REACH_M = 0.55
_CLEARANCE_EXTRA_M = 0.20
_WAYPOINT_MAX_TICKS = 300  # ~5 s: after that the plan is stale, re-plan
_UNSAFE_MARGIN_M = 0.60


class WaypointCandidatePolicy:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._waypoint: tuple[float, float] | None = None
        self._waypoint_obstacle_id: str | None = None
        self._waypoint_age: int = 0

    def _choose_waypoint(self, obs: SensorObservation) -> None:
        pose = obs.observed_pose
        if pose is None:
            return
        goal_dist = math.hypot(obs.goal_rel_x_m, obs.goal_rel_y_m)
        if goal_dist < 1e-6:
            return
        ux, uy = obs.goal_rel_x_m / goal_dist, obs.goal_rel_y_m / goal_dist
        perp_x, perp_y = -uy, ux
        tracks = {t.id: t for t in obs.tracks}

        blocking = None
        for obstacle in obs.obstacles:
            along = obstacle.rel_x_m * ux + obstacle.rel_y_m * uy
            lateral = ux * obstacle.rel_y_m - uy * obstacle.rel_x_m
            if along <= 0.0:
                continue
            if abs(lateral) < obstacle.radius_m + 0.9 and obstacle.distance_m < 3.0:
                if blocking is None or obstacle.distance_m < blocking.distance_m:
                    blocking = obstacle
        if blocking is None:
            return

        # Side: behind the obstacle's lateral motion (the vacating side);
        # fall back to the side opposite its current lane offset.
        lateral = ux * blocking.rel_y_m - uy * blocking.rel_x_m
        track = tracks.get(blocking.id)
        side: float
        if track is not None and track.confident:
            lateral_velocity = ux * track.vy_mps - uy * track.vx_mps
            if abs(lateral_velocity) > 0.05:
                side = -math.copysign(1.0, lateral_velocity)
            else:
                side = -math.copysign(1.0, lateral) if lateral != 0 else 1.0
        else:
            side = -math.copysign(1.0, lateral) if lateral != 0 else 1.0

        offset = (
            blocking.radius_m
            + 0.25  # robot body radius is not in the observation; scenario-typical
            + _CLEARANCE_EXTRA_M
        )
        obstacle_world_x = pose["x_m"] + blocking.rel_x_m
        obstacle_world_y = pose["y_m"] + blocking.rel_y_m
        self._waypoint = (
            obstacle_world_x + perp_x * side * offset,
            obstacle_world_y + perp_y * side * offset,
        )
        self._waypoint_obstacle_id = blocking.id
        self._waypoint_age = 0

    def __call__(self, obs: SensorObservation, config: PolicyConfig) -> ControlCommand:
        pose = obs.observed_pose
        if pose is None:
            return _core_navigation_law(obs, config)

        if self._waypoint is None:
            self._choose_waypoint(obs)

        if self._waypoint is not None:
            self._waypoint_age += 1
            wx, wy = self._waypoint
            rel_x, rel_y = wx - pose["x_m"], wy - pose["y_m"]
            # Drop a stale plan, or one the obstacle has swept back onto:
            # circling a dead waypoint is exactly how the stuck rule fires.
            obstacle_back = any(
                math.hypot(pose["x_m"] + o.rel_x_m - wx, pose["y_m"] + o.rel_y_m - wy)
                < o.radius_m + _UNSAFE_MARGIN_M
                for o in obs.obstacles
            )
            if self._waypoint_age > _WAYPOINT_MAX_TICKS or obstacle_back:
                self._waypoint = None
                self._waypoint_obstacle_id = None
                self._choose_waypoint(obs)
                if self._waypoint is not None:
                    wx, wy = self._waypoint
                    rel_x, rel_y = wx - pose["x_m"], wy - pose["y_m"]

        if self._waypoint is not None:
            wx, wy = self._waypoint
            rel_x, rel_y = wx - pose["x_m"], wy - pose["y_m"]
            if math.hypot(rel_x, rel_y) < _REACH_M:
                # Waypoint reached: resume to the real goal.
                self._waypoint = None
                self._waypoint_obstacle_id = None
            else:
                shifted = obs.model_copy(
                    update={
                        "goal_rel_x_m": rel_x,
                        "goal_rel_y_m": rel_y,
                        "goal_distance_m": math.hypot(rel_x, rel_y),
                    }
                )
                return _core_navigation_law(shifted, config)

        return _core_navigation_law(obs, config)
