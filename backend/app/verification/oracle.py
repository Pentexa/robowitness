"""Independent deterministic oracle rule evaluator."""

from typing import List, Tuple
from app.schemas.scenario import OracleSpec
from app.schemas.telemetry import OracleStatus, RunMetrics


def evaluate_oracle(
    metrics: RunMetrics, oracle_spec: OracleSpec, reason_codes: List[str]
) -> Tuple[OracleStatus, List[str]]:
    """Determine oracle verdict strictly from measured metrics and rules."""
    final_reasons = list(reason_codes)

    if metrics.total_ticks == 0:
        return "INCONCLUSIVE", ["MISSING_TELEMETRY"]

    if oracle_spec.collision_free and metrics.collision_detected:
        if "COLLISION" not in final_reasons:
            final_reasons.append("COLLISION")

    if metrics.min_clearance_m < oracle_spec.min_clearance_m:
        if "MIN_CLEARANCE_VIOLATION" not in final_reasons:
            final_reasons.append("MIN_CLEARANCE_VIOLATION")

    if oracle_spec.must_reach_goal and not metrics.goal_reached:
        if "GOAL_NOT_REACHED" not in final_reasons:
            final_reasons.append("GOAL_NOT_REACHED")

    if metrics.timeout_detected:
        if "TIMEOUT" not in final_reasons:
            final_reasons.append("TIMEOUT")

    if metrics.stuck_detected:
        if "STUCK" not in final_reasons:
            final_reasons.append("STUCK")

    if final_reasons:
        return "FAIL", final_reasons

    if metrics.goal_reached and not metrics.collision_detected:
        return "PASS", []

    return "INCONCLUSIVE", ["INCOMPLETE_EVALUATION"]
