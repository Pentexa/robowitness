"""Live-stack E2E smoke: exercises the RUNNING services over real HTTP.

Requires backend :8000 + worker + (optionally) web :3000 already up.
Covers: health -> reference run (FAIL) -> investigation -> battery card ->
real-log import -> metrics. Exits non-zero on the first broken expectation.

Run:  python scripts/e2e_live_stack.py
"""
import json
import sys
import time
import urllib.request

API = "http://127.0.0.1:8000"
WEB = "http://127.0.0.1:3000"


def call(method: str, path: str, body: dict | None = None, expect: int = 200) -> dict:
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Content-Type", "application/json")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as resp:
            payload = json.loads(resp.read().decode() or "{}")
            status = resp.status
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        payload, status = {}, exc.code
    assert status == expect, f"{method} {path} -> {status} (expected {expect})"
    return payload


def wait_job(job_id: str, timeout_s: int = 180) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        job = call("GET", f"/api/jobs/{job_id}")
        if job["status"] in ("completed", "failed", "cancelled"):
            return job
        time.sleep(1.5)
    raise AssertionError(f"job {job_id} timed out")


def main() -> int:
    print("1) health")
    health = call("GET", "/api/health")
    assert health["status"] == "healthy" and health["worker_active"], health

    print("2) reference baseline run must FAIL with collision")
    scenario = call("GET", "/api/scenarios/reference")[0]
    job = call(
        "POST",
        "/api/runs",
        {"scenario": scenario, "policy": {"id": "baseline-v1"}},
        expect=202,
    )
    wait_job(job["job_id"])
    run = call("GET", f"/api/runs/{job['result_id']}")
    assert run["oracle_status"] == "FAIL" and run["metrics"]["collision_detected"], run
    print(f"   {run['run_id']}: FAIL collision min={run['metrics']['min_clearance_m']} m")

    print("3) investigation must be grounded (tick-level)")
    inv = call("POST", f"/api/failures/{job['result_id']}/investigate", {})
    assert inv["failure_tick"] >= 300 and inv["suggested_patch"], inv
    print(f"   failure tick {inv['failure_tick']} via {inv['provenance']}")

    print("4) exam battery produces a report card")
    battery = call(
        "POST",
        "/api/batteries",
        {
            "robot_id": "robot-turtlebot3-waffle-pi",
            "scenario_ids": ["RW-LIB-009"],
            "policy": {"id": "baseline-v1"},
        },
        expect=202,
    )
    wait_job(battery["job_id"])
    card = call("GET", f"/api/batteries/{battery['result_id']}")
    assert card["summary"]["passed"] == 1, card["summary"]
    print(f"   karne {card['summary']['passed']}/{card['summary']['total']} PASS")

    print("5) real-log import judged as near-miss")
    csv_log = (
        "t_s,x_m,y_m,yaw_rad,min_obstacle_distance_m\n"
        "0.0,1.0,4.0,0.0,2.0\n1.0,5.0,4.0,0.0,0.10\n2.0,10.8,4.0,0.0,1.5\n"
    )
    imported = call(
        "POST",
        "/api/imports/telemetry",
        {
            "name": "e2e-live.csv",
            "format": "csv",
            "content": csv_log,
            "goal": {"x_m": 11.0, "y_m": 4.0},
        },
        expect=201,
    )
    assert imported["oracle_status"] == "FAIL" and imported["near_miss"], imported
    print("   REAL_LOG near-miss judged correctly")

    print("6) web dashboard reachable")
    try:
        with urllib.request.urlopen(WEB, timeout=10) as resp:
            assert resp.status == 200
        print("   web 200")
    except Exception as exc:
        print(f"   [warn] web unreachable ({exc}) — backend journeys still passed")

    print("\nE2E LIVE STACK: ALL PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
