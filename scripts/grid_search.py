import itertools
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
dev_sets = []
for name in ("manifest_v1_dev.json", "manifest_v2_eval.json", "manifest.json"):
    dev_sets += json.load(open(ROOT / "scenarios" / "holdout" / name))["scenarios"]
print("dev cases:", len(dev_sets), flush=True)


def run_case(spec, pol):
    r = SimulationRunner(spec, pol, configurable_policy)
    f, m, rr = r.run()
    st, _ = evaluate_oracle(m, spec.oracle, rr)
    return st, m


results = []
grid = list(itertools.product([0.55, 0.60, 0.65], [0.90, 1.00], [0.80, 1.00, 1.20], [3.5, 4.0]))
for i, (sp, safe, hor, br) in enumerate(grid):
    pol = PolicyConfig(id="grid-%02d" % i, max_speed_mps=sp, safe_distance_m=safe,
                       reaction_margin_m=0.20, brake_gain=br,
                       obstacle_prediction_horizon_s=hor)
    st, _ = run_case(ref, pol)
    if st != "PASS":
        print("grid-%02d REF FAIL -> skip" % i, flush=True)
        continue
    npass, fails, min_margin = 0, [], 9.0
    for item in dev_sets:
        spec = ScenarioSpec.model_validate(item)
        st2, m2 = run_case(spec, pol)
        if st2 == "PASS":
            npass += 1
            min_margin = min(min_margin, m2.min_clearance_m)
        else:
            fails.append(spec.id)
    results.append((npass, min_margin, i, sp, safe, hor, br, fails))
    print("grid-%02d sp=%s safe=%s hor=%s br=%s DEV %d/60 margin=%.3f fails=%s"
          % (i, sp, safe, hor, br, npass, min_margin, fails), flush=True)

results.sort(key=lambda r: (-r[0], -r[1]))
print("=== TOP 5 ===", flush=True)
for r in results[:5]:
    print(r, flush=True)
