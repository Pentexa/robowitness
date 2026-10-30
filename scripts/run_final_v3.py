import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8000"


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())


def get(path):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=60).read().decode())


ref = json.load(open(ROOT / "scenarios" / "reference" / "moving_obstacle_latency.json"))
r = post("/api/runs", {"scenario": ref, "policy": {"id": "baseline-v1"}})
print("baseline job:", r, flush=True)
run_id = r["result_id"]

import time
for _ in range(60):
    j = get("/api/jobs/" + r["job_id"])
    if j["status"] in ("completed", "failed", "cancelled"):
        break
    time.sleep(2)
print("baseline job status:", j["status"], flush=True)

F1 = {"schema_version": "1.0", "id": "candidate-final-v3", "max_speed_mps": 0.60,
      "safe_distance_m": 1.00, "reaction_margin_m": 0.20, "brake_gain": 4.0,
      "obstacle_prediction_horizon_s": 1.00}
rv = post("/api/fixes/verify", {"baseline_run_id": run_id, "candidate_policy": F1})
print("verify job:", rv, flush=True)
for _ in range(300):
    vj = get("/api/jobs/" + rv["job_id"])
    if vj["status"] in ("completed", "failed", "cancelled"):
        break
    time.sleep(2)
print("verify job status:", vj["status"], vj.get("progress"), flush=True)
rec = get("/api/verifications/" + rv["result_id"])
print("VERDICT:", rec["verdict"], flush=True)
for g in rec["gates"]:
    print(" ", g["gate_id"], g["status"], g.get("reason_codes", []), flush=True)
    if g["gate_id"] == "GATE_3_HOLDOUT":
        for c in g["details"].get("cases", []):
            if c["oracle_status"] != "PASS":
                print("   FAIL", c["scenario_id"], c["reasons"],
                      c["min_clearance_m"], c["goal_reached"], flush=True)
print("artifact:", rec["artifact_dir"], flush=True)
