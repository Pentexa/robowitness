"""CI gate: run a RoboWitness battery via API and fail the pipeline if it misses thresholds.

Usage:
  RW_API_URL=http://127.0.0.1:8000 RW_API_KEY=... python scripts/ci_battery_gate.py \
      --robot robot-turtlebot3-waffle-pi --profile-file policy.json \
      --min-pass-rate 0.8 --max-collisions 0

Exit codes: 0 gate passed, 1 gate failed, 2 infrastructure error.
The backend worker must be running (jobs are executed by the worker process).
"""

import argparse
import json
import os
import sys
import time
import urllib.request

API = os.environ.get("RW_API_URL", "http://127.0.0.1:8000").rstrip("/")
KEY = os.environ.get("RW_API_KEY", "")
WORKSPACE = os.environ.get("RW_WORKSPACE", "")


def call(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Content-Type", "application/json")
    if KEY:
        req.add_header("X-API-Key", KEY)
    if WORKSPACE:
        req.add_header("X-Workspace-Id", WORKSPACE)
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(req, data=data, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser(description="RoboWitness CI battery gate")
    parser.add_argument("--robot", required=True)
    parser.add_argument("--policy-file", required=True, help="PolicyConfig JSON file")
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    parser.add_argument("--max-collisions", type=int, default=0)
    parser.add_argument("--max-near-misses", type=int, default=None)
    parser.add_argument("--timeout-s", type=int, default=300)
    args = parser.parse_args()

    try:
        policy = json.loads(open(args.policy_file, encoding="utf-8-sig").read())
        job = call("POST", "/api/batteries", {"robot_id": args.robot, "policy": policy})
        deadline = time.time() + args.timeout_s
        state = {}
        while time.time() < deadline:
            state = call("GET", f"/api/jobs/{job['job_id']}")
            if state["status"] in ("completed", "failed", "cancelled"):
                break
            time.sleep(2)
        if state.get("status") != "completed":
            print(f"[gate] ERROR: battery job did not complete: {state}")
            return 2
        card = call("GET", f"/api/batteries/{job['result_id']}")
    except Exception as exc:
        print(f"[gate] ERROR: {exc}")
        return 2

    s = card["summary"]
    pass_rate = s["passed"] / s["total"] if s["total"] else 0.0
    reasons = []
    if pass_rate < args.min_pass_rate:
        reasons.append(f"pass rate {pass_rate:.2f} < {args.min_pass_rate:.2f}")
    if s["collisions"] > args.max_collisions:
        reasons.append(f"collisions {s['collisions']} > {args.max_collisions}")
    if args.max_near_misses is not None and s["near_misses"] > args.max_near_misses:
        reasons.append(f"near misses {s['near_misses']} > {args.max_near_misses}")

    print(
        f"[gate] battery {card['battery_id']}: {s['passed']}/{s['total']} passed, "
        f"collisions={s['collisions']}, near_misses={s['near_misses']}"
    )
    if reasons:
        print("[gate] FAILED: " + "; ".join(reasons))
        return 1
    print("[gate] PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
