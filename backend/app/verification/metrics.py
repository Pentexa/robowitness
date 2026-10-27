"""Simulation metrics extraction and computation."""
from typing import List
from app.schemas.telemetry import RunMetrics, TelemetryFrame

def compute_run_metrics(frames: List[TelemetryFrame]) -> RunMetrics:
    if not frames:
        return RunMetrics(
            total_ticks=0,
            sim_duration_s=0.0,
            min_clearance_m=0.0,
            goal_reached=False,
            collision_detected=False,
            stuck_detected=False,
            timeout_detected=True,
        )

    min_clearance = min(f.clearance_m for f in frames)
    has_collision = any(any(e.type == "COLLISION" for e in f.events) for f in frames)
    has_goal = any(any(e.type == "GOAL_REACHED" for e in f.events) for f in frames)
    has_stuck = any(any(e.type == "STUCK" for e in f.events) for f in frames)
    has_timeout = any(any(e.type == "TIMEOUT" for e in f.events) for f in frames)

    return RunMetrics(
        total_ticks=len(frames),
        sim_duration_s=frames[-1].sim_time_s,
        min_clearance_m=min_clearance,
        goal_reached=has_goal,
        collision_detected=has_collision,
        stuck_detected=has_stuck,
        timeout_detected=has_timeout,
    )
