"""Paired simulation comparison evaluator (Gate 2)."""

import hashlib
import json
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.schemas.telemetry import RunMetrics
from app.schemas.verification import GateResult


def compute_spec_hash(spec: ScenarioSpec) -> str:
    serialized = json.dumps(spec.model_dump(), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_policy_hash(policy: PolicyConfig) -> str:
    serialized = json.dumps(policy.model_dump(), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def evaluate_paired_comparison(
    baseline_metrics: RunMetrics,
    candidate_metrics: RunMetrics,
    baseline_reasons: list,
    candidate_reasons: list,
) -> GateResult:
    """Evaluate whether candidate improves on baseline in the paired test."""
    no_collision = not candidate_metrics.collision_detected
    reached_goal = candidate_metrics.goal_reached

    passed = no_collision and reached_goal and not candidate_reasons

    status = "PASS" if passed else "FAIL"
    reasons = candidate_reasons if not passed else []

    return GateResult(
        gate_id="GATE_2_PAIRED",
        name="Paired Comparison Gate",
        status=status,
        reason_codes=reasons,
        details={
            "baseline_min_clearance_m": baseline_metrics.min_clearance_m,
            "candidate_min_clearance_m": candidate_metrics.min_clearance_m,
            "baseline_goal_reached": baseline_metrics.goal_reached,
            "candidate_goal_reached": candidate_metrics.goal_reached,
            "baseline_collision": baseline_metrics.collision_detected,
            "candidate_collision": candidate_metrics.collision_detected,
        },
    )
