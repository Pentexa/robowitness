"""Frozen 20-holdout evaluator (Gate 3)."""
import json
from pathlib import Path
from typing import Dict, List
from app.policies.configurable import configurable_policy
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.schemas.verification import GateResult, HoldoutSummary
from app.simulation.runner import SimulationRunner
from app.verification.oracle import evaluate_oracle

def evaluate_holdouts(candidate_policy: PolicyConfig, holdout_manifest_path: Path) -> GateResult:
    with open(holdout_manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenarios = manifest.get("scenarios", [])
    if len(scenarios) < 20:
        return GateResult(
            gate_id="GATE_3_HOLDOUT",
            name="Frozen Holdout Gate",
            status="INCONCLUSIVE",
            reason_codes=["INSUFFICIENT_HOLDOUT_COUNT"],
            details={"holdout_count": len(scenarios)}
        )

    passed_count = 0
    details = []

    for item in scenarios:
        spec = ScenarioSpec.model_validate(item)
        runner = SimulationRunner(spec, candidate_policy, configurable_policy)
        frames, metrics, raw_reasons = runner.run()
        oracle_status, reasons = evaluate_oracle(metrics, spec.oracle, raw_reasons)

        is_pass = (oracle_status == "PASS")
        if is_pass:
            passed_count += 1

        details.append({
            "scenario_id": spec.id,
            "seed": spec.seed,
            "oracle_status": oracle_status,
            "reasons": reasons,
            "min_clearance_m": metrics.min_clearance_m,
            "goal_reached": metrics.goal_reached,
        })

    all_passed = (passed_count == len(scenarios))
    status = "PASS" if all_passed else "FAIL"

    return GateResult(
        gate_id="GATE_3_HOLDOUT",
        name="Frozen Holdout Gate",
        status=status,
        reason_codes=[] if all_passed else ["HOLDOUT_FAILURE"],
        details={
            "total_cases": len(scenarios),
            "passed_cases": passed_count,
            "cases": details,
        }
    )
