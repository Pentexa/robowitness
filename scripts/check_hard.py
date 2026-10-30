import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.policies.baseline import baseline_policy
from app.policies.configurable import configurable_policy
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.simulation.runner import SimulationRunner
from app.verification.oracle import evaluate_oracle

ref = ScenarioSpec.model_validate_json(
    (ROOT / "scenarios" / "reference" / "moving_obstacle_latency.json").read_text())

# 1. Baseline must be bit-identical (horizon=0 path untouched).
r = SimulationRunner(ref, PolicyConfig(), configurable_policy)
frames, metrics, reasons = r.run()
print("baseline:", evaluate_oracle(metrics, ref.oracle, reasons),
      "ticks=", len(frames), "min_clear=", metrics.min_clearance_m, flush=True)
assert (len(frames), metrics.min_clearance_m) == (359, 0.0016)

b2 = SimulationRunner(ref, PolicyConfig(), baseline_policy)
f2, m2, _ = b2.run()
assert len(f2) == len(frames) and m2.min_clearance_m == metrics.min_clearance_m
print("baseline identical across policy entry points", flush=True)

# 2. Hard cases with F1 + anti-sitting-duck.
F1 = PolicyConfig(id="candidate-final-v2", max_speed_mps=0.60, safe_distance_m=1.00,
                  reaction_margin_m=0.20, brake_gain=4.0, obstacle_prediction_horizon_s=1.00)
by_id = {}
for name in ("manifest_v1_dev.json", "manifest_v2_eval.json", "manifest.json"):
    for s in json.load(open(ROOT / "scenarios" / "holdout" / name))["scenarios"]:
        by_id[s["id"]] = s
for cid in ("RW-HLD2-006", "RW-HLD2-017", "RW-HLD3-009", "RW-HLD3-019", "RW-HLD3-020",
            "RW-HLD2-004", "RW-HLD2-005"):
    spec = ScenarioSpec.model_validate(by_id[cid])
    f, m, rr = SimulationRunner(spec, F1, configurable_policy).run()
    st, rs = evaluate_oracle(m, spec.oracle, rr)
    print(cid, st, rs, "ticks=", len(f), "min_clear=", m.min_clearance_m, flush=True)
