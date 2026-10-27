"""Critical regression suite evaluator (Gate 4)."""
import json
from pathlib import Path
from typing import List
from app.policies.configurable import configurable_policy
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.schemas.verification import GateResult
from app.simulation.runner import SimulationRunner
from app.verification.oracle import evaluate_oracle

def evaluate_regressions(candidate_policy: PolicyConfig, regression_dir: Path) -> GateResult:
    scenario_files = list(regression_dir.glob("*.json"))
    if not scenario_files:
        return GateResult(
            gate_id="GATE_4_REGRESSION",
            name="Critical Regression Gate",
            status="INCONCLUSIVE",
            reason_codes=["MISSING_REGRESSION_SCENARIOS"],
            details={}
        )

    passed_count = 0
    details = []

    for s_file in scenario_files:
        with open(s_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        spec = ScenarioSpec.model_validate(data)

        runner = SimulationRunner(spec, candidate_policy, configurable_policy)
        frames, metrics, raw_reasons = runner.run()
        oracle_status, reasons = evaluate_oracle(metrics, spec.oracle, raw_reasons)

        is_pass = (oracle_status == "PASS")
        if is_pass:
            passed_count += 1

        details.append({
            "scenario_id": spec.id,
            "oracle_status": oracle_status,
            "reasons": reasons,
            "goal_reached": metrics.goal_reached,
        })

    all_passed = (passed_count == len(scenario_files))
    status = "PASS" if all_passed else "FAIL"

    return GateResult(
        gate_id="GATE_4_REGRESSION",
        name="Critical Regression Gate",
        status=status,
        reason_codes=[] if all_passed else ["REGRESSION_FAILURE"],
        details={
            "total_cases": len(scenario_files),
            "passed_cases": passed_count,
            "cases": details,
        }
    )
