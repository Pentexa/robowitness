"""Judge an imported real-robot track with the same rules as the simulator.

No simulation is run here: the track was measured on a real robot elsewhere.
The verdict is only as good as the logged obstacle distances.
"""

import math
from typing import List, Tuple
from app.schemas.telemetry_import import ImportedFrame, ImportMetrics

MAX_FRAMES = 20_000


def evaluate_imported_track(
    frames: List[ImportedFrame],
    goal,
    goal_radius_m: float,
    min_clearance_limit_m: float,
) -> Tuple[str, List[str], ImportMetrics]:
    if len(frames) > MAX_FRAMES:
        raise ValueError(f"Too many frames: {len(frames)} > {MAX_FRAMES}")
    for prev, cur in zip(frames, frames[1:]):
        if cur.t_s < prev.t_s:
            raise ValueError("Frame timestamps must be non-decreasing (t_s)")

    duration = round(frames[-1].t_s - frames[0].t_s, 4) if len(frames) >= 2 else 0.0
    path_length = 0.0
    for prev, cur in zip(frames, frames[1:]):
        path_length += math.hypot(cur.x_m - prev.x_m, cur.y_m - prev.y_m)

    distances = [f.min_obstacle_distance_m for f in frames if f.min_obstacle_distance_m is not None]
    min_clearance = min(distances) if distances else None
    collision = any(d <= 0.0 for d in distances)

    goal_reached = None
    final_goal_dist = None
    if goal is not None and frames:
        final_goal_dist = round(math.hypot(goal.x_m - frames[-1].x_m, goal.y_m - frames[-1].y_m), 4)
        goal_reached = final_goal_dist <= goal_radius_m

    metrics = ImportMetrics(
        frame_count=len(frames),
        duration_s=duration,
        min_clearance_m=round(min_clearance, 4) if min_clearance is not None else None,
        collision_detected=collision,
        goal_reached=goal_reached,
        final_goal_distance_m=final_goal_dist,
        path_length_m=round(path_length, 4),
    )

    if len(frames) < 2 or not distances:
        return "INCONCLUSIVE", ["MISSING_TELEMETRY"], metrics

    reasons: List[str] = []
    if collision:
        reasons.append("COLLISION")
    if min_clearance is not None and min_clearance < min_clearance_limit_m:
        reasons.append("MIN_CLEARANCE_VIOLATION")
    if goal is not None and goal_reached is False:
        reasons.append("GOAL_NOT_REACHED")

    if reasons:
        return "FAIL", reasons, metrics
    if goal is not None and goal_reached:
        return "PASS", [], metrics
    if goal is None and not collision:
        # No goal to check: clear run with acceptable clearance counts as PASS
        # for the safety criteria that could be measured.
        return "PASS", [], metrics
    return "INCONCLUSIVE", ["INCOMPLETE_EVALUATION"], metrics
