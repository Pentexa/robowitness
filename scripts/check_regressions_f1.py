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

F1 = PolicyConfig(id="candidate-final-v2", max_speed_mps=0.60, safe_distance_m=1.00,
                  reaction_margin_m=0.20, brake_gain=4.0, obstacle_prediction_horizon_s=1.00)
reg = sorted((ROOT / "scenarios" / "regression").glob("*.json"))
ok = True
for f in reg:
    spec = ScenarioSpec.model_validate_json(f.read_text(encoding="utf-8"))
    frames, m, rr = SimulationRunner(spec, F1, configurable_policy).run()
    st, rs = evaluate_oracle(m, spec.oracle, rr)
    print(f.name, st, rs, "min_clear=", m.min_clearance_m, "goal=", m.goal_reached)
    ok = ok and (st == "PASS")
print("REGRESSIONS:", "ALL PASS" if ok else "FAILURES PRESENT")
