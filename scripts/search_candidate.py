import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.policies.configurable import configurable_policy
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.simulation.runner import SimulationRunner
from app.verification.oracle import evaluate_oracle

ref = ScenarioSpec.model_validate_json(
    (ROOT / "scenarios" / "reference" / "moving_obstacle_latency.json").read_text())
dev = json.load(open(ROOT / "scenarios" / "holdout" / "manifest_v1_dev.json"))["scenarios"]

CONFIGS = {
    "F1": dict(max_speed_mps=0.60, safe_distance_m=1.00, reaction_margin_m=0.20, brake_gain=4.0, obstacle_prediction_horizon_s=1.00),
    "F2": dict(max_speed_mps=0.55, safe_distance_m=0.90, reaction_margin_m=0.15, brake_gain=3.5, obstacle_prediction_horizon_s=0.80),
    "F3": dict(max_speed_mps=0.60, safe_distance_m=0.80, reaction_margin_m=0.15, brake_gain=3.0, obstacle_prediction_horizon_s=0.60),
    "F4": dict(max_speed_mps=0.65, safe_distance_m=0.90, reaction_margin_m=0.15, brake_gain=3.5, obstacle_prediction_horizon_s=0.80),
    "F5": dict(max_speed_mps=0.55, safe_distance_m=1.00, reaction_margin_m=0.20, brake_gain=4.0, obstacle_prediction_horizon_s=1.20),
    "F6": dict(max_speed_mps=0.50, safe_distance_m=0.90, reaction_margin_m=0.15, brake_gain=3.5, obstacle_prediction_horizon_s=1.00),
}


def run_case(spec, pol):
    r = SimulationRunner(spec, pol, configurable_policy)
    f, m, rr = r.run()
    return evaluate_oracle(m, spec.oracle, rr) + (m, len(f))


for name, kw in CONFIGS.items():
    pol = PolicyConfig(id="dev-%s" % name, **kw)
    st, rs, m, n = run_case(ref, pol)
    line = "%s REF: %s %s ticks=%d min_clear=%s" % (name, st, rs, n, m.min_clearance_m)
    if st == "PASS":
        npass, fails = 0, []
        for item in dev:
            spec = ScenarioSpec.model_validate(item)
            st2, rs2, m2, _ = run_case(spec, pol)
            if st2 == "PASS":
                npass += 1
            else:
                fails.append((spec.id, rs2, m2.min_clearance_m))
        line += " | DEV %d/20 FAILS=%s" % (npass, fails)
    print(line, flush=True)
