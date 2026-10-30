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
dev = []
for name in ("manifest_v1_dev.json", "manifest_v2_eval.json", "manifest.json"):
    dev += json.load(open(ROOT / "scenarios" / "holdout" / name))["scenarios"]

POL = PolicyConfig(id="candidate-final-v2", max_speed_mps=0.60, safe_distance_m=1.00,
                   reaction_margin_m=0.20, brake_gain=4.0, obstacle_prediction_horizon_s=1.00)

st, rs, m, n = None, None, None, 0
r = SimulationRunner(ref, POL, configurable_policy)
f, m, rr = r.run()
st, rs = evaluate_oracle(m, ref.oracle, rr)
print("REF:", st, rs, "ticks=", len(f), "min_clear=", m.min_clearance_m, flush=True)

npass, fails, margin = 0, [], 9.0
for item in dev:
    spec = ScenarioSpec.model_validate(item)
    r2 = SimulationRunner(spec, POL, configurable_policy)
    f2, m2, r2r = r2.run()
    st2, rs2 = evaluate_oracle(m2, spec.oracle, r2r)
    if st2 == "PASS":
        npass += 1
        margin = min(margin, m2.min_clearance_m)
    else:
        fails.append((spec.id, rs2, m2.min_clearance_m))
print("DEV %d/%d margin=%.3f fails=%s" % (npass, len(dev), margin, fails), flush=True)
